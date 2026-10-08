# Attempts log

Each entry records an approach that failed, what broke, and what came next.

## 2026-10-08: Task 1, track URDF would not load

- Tried: write each URDF as one long line of XML. The track has about 150 visual and collision tags.
- Broke: `p.loadURDF` failed with `XML_ERROR_PARSING_ATTRIBUTE ... Line number=4`. Python's XML parser read the same file without error. The small models loaded fine.
- Next: write one tag per line. The same track then loaded. The writer now does this for every URDF.

## 2026-10-08: Task 1, the racer stopped against a checkpoint gate

- Tried: drive the racer from the start grid to the turn two apex with pure pursuit on the wheel motors.
- Broke: the car stopped at x = 6.77, y = -1.02 in turn one, 13.8 m short of the goal. I had set each gate's yaw so its posts stood on the racing line, not beside the track.
- Next: set each gate's yaw to the track heading at that point, so the posts sit outside the track edges. The same drive then reached turn two within 4.9 cm and the finish line within 4.9 cm. No fallback to `resetBasePositionAndOrientation` was needed for the drive.

## 2026-10-08: Task 1, the low corner camera could not see the robot

- Tried: a corner camera at (-11, -7.5) and 1.2 m high, looking at the infield.
- Broke: a light tower stood right in front of the lens and filled the middle of the image. At the finish line the robot covered only 2 pixels in the segmentation mask, because the front straight barriers (0.43 m tall) hid it.
- Next: moved that light tower to the south east corner, and raised the camera to 1.5 m with a narrower view. The robot now covers 98 to 333 pixels in that view.

## 2026-10-08: Task 1, false shadow band in the top-down view

- Tried: the tiny renderer with shadows on for all three cameras.
- Broke: the top-down image showed a dark diagonal band across the grass. It moved when the light direction changed, so it came from the shadow map, not from any object.
- Next: shadows off for the top-down camera only. The two side views keep shadows.

