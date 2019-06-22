# xray-skls-file-browser
[Blender](http://www.blender.org/) add-on for animations collection browser for X-Ray/Stalker engine .skls files.
Attention. Since this add-on wide used python annotations, it requires at least python 3.6.

## Workflow with .skls files

1. Use [blender-xray](https://github.com/PavelBlend/blender-xray) (by PavelBlend) add-on to import .object file with X-Ray armature bones:
![](/images/Blender_import_object.png)

1. Select .object file:
![](/images/Blender_import_object_file.png)

1. Press **Open .skls file** button on the panel **Skls file browser**:
![](/images/Blender_open_skls_file.png)

1. Select .skls file:
![](/images/Blender_open_skls_file2.png)
This kind of files may contains thousands animations. So opening may take tens seconds. Upon opening completion an animations list will fills with animations names.

1. Select animation in the animations list on the panel **Skls file browser**:
![](/images/Blender_animation.png)
Use **Timeline** to examine and **Dope Sheet** to edit the animation with power of Blender.

## Object and animation sources
X-Ray engine store the meshes and armature with **.ogf** files. This files needs to convert to **.object** files by [converter.exe](https://bitbucket.org/stalker/xray_re-tools/downloads/) (be attention to X-Ray version). Usually the source files is packed into a group of files with names pattern: **gamedata.db***. To unpack use converter.exe.

hunter_1.object file is from **Shadow Of Chernobyl** with **Goldsphere Ending** global add-on: gamedata/meshes/actors/hunter_1.ogf.

stalker_animation.skls file: gamedata/meshes/actors/stalker_animation.omf.

> Thanks to X-Ray/Stalker engine developers.
Thanks to Vakhurin Sergey (igel), Pavel_Blend: https://github.com/PavelBlend/blender-xray.
