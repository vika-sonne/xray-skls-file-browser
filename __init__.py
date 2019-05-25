# Thanks to X-Ray/Stalker engine developers
# Thanks to Vakhurin Sergey (igel), Pavel_Blend: https://github.com/PavelBlend/blender-xray


bl_info = {
	'name' : 'X-Ray .skls File Browser',
	'description' : 'X-Ray/Stalker engine animation browser for .skls files.',
	'author' : 'Viktoria Danchenko',
	'version' : (0, 1),
	'blender' : (2, 79, 0),
	'location' : '3D View > N Panel > Skls file browser',
	'category' : '3D View',
	'wiki_url': 'https://github.com/vika-sonne/xray-skls-file-browser',
	'tracker_url': 'https://github.com/vika-sonne/xray-skls-file-browser/issues',
}


from typing import List, Dict, Optional
import bpy
from bpy.utils import register_class, unregister_class
from mathutils import Matrix, Euler
from . import xray_skls


class View3DPanel:
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'


class XRAY_OT_open_skls_file(bpy.types.Operator):
	'Shows file open dialog, reads .skls file, cleares & populates animations list'
	bl_idname = 'xray.open_skls_file'
	bl_label = 'Open .skls file'
	bl_description = 'Opens .skls file with collection of animations. Used to import X-Ray engine animations.'+\
		' To import select object with X-Ray struct of bones'
	# bl_options = {'REGISTER', 'UNDO'}

	class SklsAnimations(bpy.types.PropertyGroup):
		'Contains animation properties in animations list'
		name = bpy.props.StringProperty(name='Name')

	filepath = bpy.props.StringProperty(subtype='FILE_PATH')
	filter_glob = bpy.props.StringProperty(default='*.skls', options={'HIDDEN'})

	@classmethod
	def poll(cls, context):
		return context.active_object is not None and hasattr(context.active_object.data, 'bones')

	def execute(self, context):
		self.report({'INFO'}, 'Loading animations from .skls file: "{}"'.format(self.filepath))
		bpy.context.window.cursor_set('WAIT')
		ob = bpy.context.object
		ob.SklsAnimations.clear()
		VIEW3D_PT_skls_animations.skls_file = xray_skls.SklsFile(file_path=self.filepath)
		self.report({'INFO'}, 'Done: {} animation(s)'.format(len(VIEW3D_PT_skls_animations.skls_file.animations)))
		# fill list with animations names
		for animation_name in VIEW3D_PT_skls_animations.skls_file.animations.keys():
			newitem = ob.SklsAnimations.add()
			newitem.name = animation_name
		bpy.context.window.cursor_set('DEFAULT')
		return {'FINISHED'}

	def invoke(self, context, event):
		wm = context.window_manager
		wm.fileselect_add(operator=self)
		return {'RUNNING_MODAL'}


class VIEW3D_PT_skls_animations(View3DPanel, bpy.types.Panel):
	'Contains open .skls file operator, animations list'
	bl_label = 'Skls file browser'

	skls_file: Optional[xray_skls.SklsFile] = None # pure python hold variable of .skls file buffer instance

	def draw(self, context):
		layout = self.layout

		col = layout.column(align=True)
		col.operator(operator='xray.open_skls_file', text='Open skls file...')
		# if VIEW3D_PT_skls_animations.skls_file:
		# 	col.label(text=VIEW3D_PT_skls_animations.skls_file.file_path)
		# else:
		# 	col.label(text='')
		if hasattr(context.object, 'SklsAnimations'):
			layout.template_list(listtype_name='AnimationList_item', list_id='compact',
			dataptr=context.object, propname='SklsAnimations',
			active_dataptr=context.object, active_propname='SklsAnimations_index', rows=15)#, type='COMPACT')


class AnimationList_item(bpy.types.UIList):

	def draw_item(self, _context, layout, _data, item : XRAY_OT_open_skls_file.SklsAnimations, _icon, _active_data, _active_propname):
		row = layout.row(align=True)
		row.label(text=item.name)


def animations_index_changed(self, context):
	'''Selected animation changed in .skls list'''
	# try to cancel & unlink old animation
	try:
		bpy.ops.screen.animation_cancel()
	except:
		pass
	try:
		# it can happened that unlink action is inaccessible
		bpy.ops.action.unlink()
	except:
		pass
	# get new animation name
	if not VIEW3D_PT_skls_animations.skls_file:
		return
	animation_name = self.SklsAnimations[self.SklsAnimations_index].name
	# remove previous animation if need
	ob = context.active_object
	if ob.animation_data:
		# need to remove previous animation to free the memory since .skls can contains thousand animations
		try:
			act = ob.animation_data.action
			ob.animation_data_clear()
			act.user_clear()
			bpy.data.actions.remove(action=act)
		except:
			pass
	if animation_name not in bpy.data.actions:
		# animation not imported yet # import & create animation to bpy.data.actions
		context.window.cursor_set('WAIT')
		fail_bones_names = set()
		import_animation(
			animation_name=animation_name,
			animation=VIEW3D_PT_skls_animations.skls_file.get_animation(animation_name),
			bpy_armature=ob,
			bonesmap={ b.name.lower(): b for b in ob.data.bones },
			fail_bones_names=fail_bones_names)
		context.window.cursor_set('DEFAULT')
		# try to find DopeSheet editor & set action to play
		try:
			ds = [ i for i in context.screen.areas if i.type=='DOPESHEET_EDITOR']
			if ds and not ds[0].spaces[0].action:
				ds.spaces[0].action = bpy.data.actions[animation_name]
		except:
			pass
	# assign & play a new animation
	# bpy.data.armatures[0].pose_position='POSE'
	try:
		act = bpy.data.actions[animation_name]
		if not ob.animation_data:
			ob.animation_data_create()
		ob.animation_data.action = act
	except:
		pass
	else:
		# play an action from first to last frames in cycle
		try:
			# active_scene = bpy.context.window.scene # 2.80
			context.scene.frame_start = act.frame_range[0]
			context.scene.frame_current = act.frame_range[0]
			context.scene.frame_end = act.frame_range[1]
			bpy.ops.screen.animation_play()
		except:
			pass

def import_animation(
		animation_name: str,
		animation: xray_skls.Animation,
		bpy_armature,
		bonesmap: Dict[str, bpy.types.Bone],
		fail_bones_names: List[str]) -> bpy.types.Action:

	def find_bone_exportable_parent(bpy_bone):
		def is_exportable_bone(bpy_bone) -> bool:
			return bpy_bone.xray.exportable and not bpy_bone.name.endswith('.fake')
		result = bpy_bone.parent
		while (result is not None) and not is_exportable_bone(result):
			result = result.parent
		return result

	MATRIX_BONE = Matrix((
		(1.0, 0.0, 0.0, 0.0),
		(0.0, 0.0, -1.0, 0.0),
		(0.0, 1.0, 0.0, 0.0),
		(0.0, 0.0, 0.0, 1.0)
		)).freeze()

	ret = bpy.data.actions.new(name=animation_name)
	ret.use_fake_user = True # force the animation to be kept

	for bone in animation.bones:
		tmpfc: List[bpy.types.FCurve] = [ret.fcurves.new('temp', i) for i in range(6)]
		try:
			times: Dict[float, bool] = {}
			for envelope, fcurve in zip(bone.envelopes, tmpfc):
				for key in envelope.keys:
					time = key.time * animation.fps
					times[time] = True
					fcurve.keyframe_points.insert(frame=time, value=key.value, options={'FAST'})
			armature_bone = bpy_armature.data.bones.get(bone.name, None)
			if armature_bone is None:
				armature_bone = bonesmap.get(bone.name.lower(), None)
				if armature_bone is None:
					if bone.name not in fail_bones_names:
						# warn('bone is not found', bone=bone.name)
						fail_bones_names.add(bone.name)
					continue
				if bone.name not in fail_bones_names:
					fail_bones_names.add(bone.name)
				bone.name = armature_bone.name
			data_path = 'pose.bones["' + bone.name + '"]'
			fcs: List[bpy.types.FCurve] = [
				ret.fcurves.new(data_path=data_path + '.location', index=0, action_group=bone.name),
				ret.fcurves.new(data_path=data_path + '.location', index=1, action_group=bone.name),
				ret.fcurves.new(data_path=data_path + '.location', index=2, action_group=bone.name),
				ret.fcurves.new(data_path=data_path + '.rotation_euler', index=0, action_group=bone.name),
				ret.fcurves.new(data_path=data_path + '.rotation_euler', index=1, action_group=bone.name),
				ret.fcurves.new(data_path=data_path + '.rotation_euler', index=2, action_group=bone.name)
			]
			xmat = armature_bone.matrix_local.inverted()
			real_parent = find_bone_exportable_parent(armature_bone)
			if real_parent:
				xmat = xmat * real_parent.matrix_local
			else:
				xmat = xmat * MATRIX_BONE
			for time in times:
				mat = xmat * Matrix.Translation((
					+tmpfc[0].evaluate(frame=time),
					+tmpfc[1].evaluate(frame=time),
					-tmpfc[2].evaluate(frame=time),
				)) * Euler((
					-tmpfc[4].evaluate(frame=time),
					-tmpfc[3].evaluate(frame=time),
					+tmpfc[5].evaluate(frame=time),
				), 'ZXY').to_matrix().to_4x4()
				translation = mat.to_translation()
				rotation = mat.to_euler('ZXY')
				for i in range(3):
					fcs[i + 0].keyframe_points.insert(frame=time, value=translation[i], options={'FAST'})
				for i in range(3):
					fcs[i + 3].keyframe_points.insert(frame=time, value=rotation[i], options={'FAST'})
		finally:
			for fcurve in tmpfc:
				ret.fcurves.remove(fcurve=fcurve)
	return ret

classes = (
	VIEW3D_PT_skls_animations,
	XRAY_OT_open_skls_file.SklsAnimations,
	XRAY_OT_open_skls_file,
	AnimationList_item,
)

def register():
	for _ in classes:
		register_class(_)
	bpy.types.Object.SklsAnimations = bpy.props.CollectionProperty(type=XRAY_OT_open_skls_file.SklsAnimations)
	bpy.types.Object.SklsAnimations_index = bpy.props.IntProperty(update=animations_index_changed)

def unregister():
	for _ in classes:
		unregister_class(_)
	if VIEW3D_PT_skls_animations.skls_file:
		VIEW3D_PT_skls_animations.skls_file = None
	del bpy.types.Object.SklsAnimations
	del bpy.types.Object.SklsAnimations_index

if __name__ == '__main__':
	register()
