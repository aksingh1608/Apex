"""Make a coloured copy of the TurtleBot3 Burger SDF. No ROS imports.

The copy keeps every sensor and plugin. It adds a coloured roof plate and
a rear wing (visual only, so the LiDAR rays pass through) and turns off the
odom TF, so two cars do not publish the same TF frames.
"""

from apex_race.props import geometry, material


def coloured_burger(sdf_text, model_name, rgb):
    if '<link name="base_link">' not in sdf_text:
        raise ValueError("base_link not found in the Burger SDF")
    plate = (f'<visual name="apex_roof"><pose>-0.032 0 0.205 0 0 0</pose>'
             f"{geometry('cylinder', (0.07, 0.01))}{material(rgb)}</visual>"
             f'<visual name="apex_wing"><pose>-0.115 0 0.13 0 0 0</pose>'
             f"{geometry('box', (0.03, 0.17, 0.012))}{material(rgb)}</visual>")
    out = sdf_text.replace('<link name="base_link">', '<link name="base_link">' + plate, 1)
    out = out.replace('<model name="turtlebot3_burger">', f'<model name="{model_name}">', 1)
    out = out.replace("<publish_odom_tf>true</publish_odom_tf>",
                      "<publish_odom_tf>false</publish_odom_tf>")
    return out
