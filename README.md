flumpkit
========

Introducing flumpkit for blender & Gimp. Tools for the flump animation file format.

See an example of the results here.

##[Link to result of export](http://dmg46664.github.io/demo.html)

See the following video to get started and see how this was done.

[![ScreenShot](https://raw.github.com/wiki/dmg46664/flumpkit/flumpYouTube.png)](http://www.youtube.com/watch?v=HjA2vNGEVvs)

## Mapping in blender

* Planes represent symbols (at least in the playn runtime nomenclature).
* Bones represent movie layers.

## Limitations

* blender drivers not supported for export
* Parenting bones not supported for export, hence IK also not supported.
* blender importer struggles with converting rotations from skew data (hacky)
* Exporter ignores opacity/alpha of material data.
* multiple symbols per layer functionality not supported.
* Some hard coded lines expect only one armature per blender scene.
* broken F8 reload functionality in blender when split the files of the python addon.
* blender importer and exporter don't support mapping flump ease-in/out to blender bezier curves. The exporter only supports exporting linear, but it does add keyframes to match blender bezier curves with hard coded tolerance.
* Exporter gets confused if you edit the HEAD and TAIL positions of bones after import. Don't do this, unless you want to fix the exporter :-)
* poor documentation of additional limitations ;-)

I'm unlikely to do much work on the project any time soon. But feel free to ask questions if you need help using or developing for it.

DMG
