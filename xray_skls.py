# X-Ray engine animation .skls file import module.
# Thanks to X-Ray/Stalker engine developers
# Thanks to Vakhurin Sergey (igel), Pavel_Blend: https://github.com/PavelBlend/blender-xray


import struct
import io
from typing import List, Dict, Tuple, Optional


class UnsupportedVersionError(Exception):
	def __init__(self, version: int):
		super().__init__('Usupported version: {}'.format(version))


class FastBytes:
	'''Helper functions for binary parsing'''

	@staticmethod
	def short_at(data: list, offs: int) -> int:
		return data[offs] | (data[offs + 1] << 8)

	@staticmethod
	def int_at(data: list, offs: int) -> int:
		return data[offs] | (data[offs + 1] << 8) | (data[offs + 2] << 16) | (data[offs + 3] << 24)

	@staticmethod
	def skip_str_at(data: list, offs: int) -> int:
		'Returns new offset'
		dlen = len(data)
		while (offs < dlen) and (data[offs] != 0):
			offs += 1
		return offs + 1

	@staticmethod
	def skip_str_at_a(data: list, offs: int) -> int:
		'Returns new offset'
		dlen = len(data)
		while (offs < dlen) and (data[offs] != 0xa):
			offs += 1
		return offs + 1

	@staticmethod
	def str_at(data: list, offs: int) -> Tuple[str, int]:
		'Returns string and new offset'
		new_offs = FastBytes.skip_str_at(data, offs)
		return data[offs:new_offs - 1].decode('cp1251'), new_offs


class PackedReader:
	'''Binary blob holder and processing functions'''
	__slots__ = ['__offs', '__data', '__view']
	__PREP_I = struct.Struct('<I')

	def __init__(self, data):
		self.__offs = 0
		self.__data = data
		self.__view = None

	def offset(self) -> int:
		'Returns current offset in file, bytes'
		return self.__offs

	def set_offset(self, offset: int):
		self.__offs = offset

	def getb(self, count: int) -> int:
		self.__offs += count
		return self.__data[self.__offs - count:self.__offs]

	def getf(self, fmt: str) -> list:
		size = struct.calcsize(fmt)
		self.__offs += size
		return struct.unpack_from(fmt, self.__data, self.__offs - size)

	def byte(self) -> int:
		return self.__data[self._next(1)]

	def int(self) -> int:
		return FastBytes.int_at(self.__data, self._next(4))

	def _next(self, size: int) -> int:
		offs = self.__offs
		self.__offs = offs + size
		return offs

	@staticmethod
	def prep(fmt: str):
		return struct.Struct('<' + fmt)

	def getp(self, prep) -> list:
		offs = self.__offs
		self.__offs = offs + prep.size
		return prep.unpack_from(self.__data, offs)

	def gets(self, onerror=None) -> str:
		data, offs = self.__data, self.__offs
		new_offs = self.__offs = FastBytes.skip_str_at(data, offs)
		bts = data[offs:new_offs - 1]
		try:
			return str(bts, 'cp1251')
		except UnicodeError as error:
			if onerror is None:
				raise
			onerror(error)
			return str(bts, 'cp1251', errors='replace')

	def gets_a(self, onerror=None) -> str:
		data, offs = self.__data, self.__offs
		new_offs = self.__offs = FastBytes.skip_str_at_a(data, offs)
		bts = data[offs:new_offs - 1]
		try:
			return str(bts, 'cp1251')
		except UnicodeError as error:
			if onerror is None:
				raise
			onerror(error)
			return str(bts, 'cp1251', errors='replace')

	def getv(self):
		view = self.__view
		if view is None:
			self.__view = view = memoryview(self.__data)
		return view[self.__offs:]

	def skip(self, count: int):
		self.__offs += count

	def skip_fmt(self, fmt: str):
		size = struct.calcsize(fmt)
		self.__offs += size

	def skip_s(self):
		self.__offs = FastBytes.skip_str_at(self.__data, self.__offs)


class Animation():
	'''Bones animation of .skl/.skls file'''
	__slots__ = 'name', 'range_from', 'range_to', 'fps', 'ver', 'flags', 'bone_of_part', 'speed', 'accure', 'falloff', 'power', 'bones_count', 'bones'

	def __init__(self):
		self.bones: list(Animation.Bone) = []

	def __str__(self):
		ret = 'name={}, range_from={}, range_to={}, fps={}, ver={}, flags={}, bone_of_part={}, speed={}, accure={}, falloff={}, power={}, bones_count={}\n'.format( \
			self.name, self.range_from, self.range_to, self.fps, self.ver, self.flags, self.bone_of_part, self.speed, self.accure, self.falloff, self.power, self.bones_count)
		for bone in self.bones:
			ret += '\t' + bone.name + '\n'
			for envelope in bone.envelopes:
				ret += '\t\t' + ';'.join([ '{}:{}'.format(key.time, key.value) for key in envelope.keys ]) + '\n'
		return ret

	@staticmethod
	def load_from_skl(pr: PackedReader, name: str = '') -> 'Animation':
		'''
		Args:
			pr: offset of pr - at first byte after animation name
			name: animation name to return
		'''
		ret = Animation()
		ret.name = name
		# offset of pr - at first byte after animation name
		ret.range_from, ret.range_to, ret.fps, ret.ver = pr.getf('=IIfH') # from, to, fps
		if ret.ver < 6:
			raise UnsupportedVersionError(ret.ver)
		ret.flags, ret.bone_of_part, ret.speed, ret.accure, ret.falloff, ret.power, ret.bones_count = pr.getf('=BHffffH') # flags, bone_or_part, speed, accure, falloff, power, bones_count
		for _1 in range(ret.bones_count):
			# add bone
			bone = Animation.Bone()
			bone.name = pr.gets() # name
			bone.flags = pr.skip_fmt('=B') # flags
			# add envelopes
			for _2 in range(6):
				envelope = Animation.Envelope()
				envelope.behaviours_from, envelope.behaviours_to = pr.getf('=BB') # behaviours
				# add keys
				for _3 in range(pr.getf('=H')[0]):
					key = Animation.Key()
					key.value, key.time, key.shape = pr.getf('=ffB') # value, time, shape
					if key.shape != 4:
						key.tension, key.continuity, key.bias = pr.getf('=HHH') # tension, continuity, bias
						key.params = pr.getf('=HHHH') # params[4]
					envelope.keys.append(key)
				bone.envelopes.append(envelope)
			ret.bones.append(bone)
		return ret

	@staticmethod
	def skip_animation(pr: PackedReader):
		pr.skip_fmt('=IIf') # from, to, fps
		ver = pr.getf('=H')[0] # ver
		if ver < 6:
			raise UnsupportedVersionError(ver)
		pr.skip_fmt('=BHffff') # flags, bone_or_part, speed, accure, falloff, power
		bones_count = pr.getf('=H')[0]
		for _1 in range(bones_count):
			pr.skip_s() # name
			pr.skip_fmt('=B') # flags
			# envelopes:
			for _2 in range(6):
				pr.skip_fmt('=BB') # behaviours
				# keys:
				for _3 in range(pr.getf('H')[0]):
					pr.skip_fmt('=ff') # value, time
					if pr.getf('B')[0] != 4: # shape
						pr.skip_fmt('=HHHHHHH') # tension, continuity, bias, params[4]
		if ver >= 7:
			# marks
			for _1 in range(pr.getf('I')[0]):
				pr.skip_s() # name
				pr.skip_fmt('=' + 'ff'*range(pr.getf('I')[0])) # intervals[4]

	class Bone():
		__slots__ = 'name', 'flags', 'envelopes'

		def __init__(self):
			self.envelopes: list(Animation.Envelope) = []

	class Envelope():
		__slots__ = 'behaviours_from', 'behaviours_to', 'keys_count', 'keys'

		def __init__(self):
			self.keys: list(Animation.Key) = []

	class Key():
		__slots__ = 'value', 'time', 'shape', 'tension', 'continuity', 'bias', 'params'


class SklsFile():
	'''
	Used to read animations from .skls file.
	Because .skls file can has big size and reading may take long time, so the animations cached by byte offset in file.
	Holds entire .skls file in memory as binary blob.
	'''
	__slots__ = 'pr', 'file_path', 'animations'

	def __init__(self, file_path: str):
		self.file_path = file_path
		self.animations: Dict[str, int] = {} # cached animations (name: offset)
		with io.open(file_path, mode='rb') as f:
			# read entire .skls file into memory
			self.pr = PackedReader(f.read())
		self._index_animations()

	def _index_animations(self):
		'''Fills the cache (self.animations) by processing entire binary blob'''
		animations_count = self.pr.getf('I')[0]
		for _ in range(animations_count):
			# index animation
			name = self.pr.gets() # name
			self.animations[name] = self.pr.offset() # first byte after name
			Animation.skip_animation(self.pr)

	def get_animation(self, name: str) -> Animation:
		self.pr.set_offset(self.animations[name])
		return Animation.load_from_skl(self.pr, name)
