"""SDF snippets for circuit props, built only from primitives. No ROS imports."""

import math


def material(rgb, emissive=None):
    r, g, b = rgb
    text = (f"<material><ambient>{r} {g} {b} 1</ambient>"
            f"<diffuse>{r} {g} {b} 1</diffuse>")
    if emissive:
        er, eg, eb = emissive
        text += f"<emissive>{er} {eg} {eb} 1</emissive>"
    return text + "</material>"


def geometry(shape, size):
    if shape == "box":
        return f"<geometry><box><size>{size[0]:.4f} {size[1]:.4f} {size[2]:.4f}</size></box></geometry>"
    if shape == "cylinder":
        return (f"<geometry><cylinder><radius>{size[0]:.4f}</radius>"
                f"<length>{size[1]:.4f}</length></cylinder></geometry>")
    if shape == "sphere":
        return f"<geometry><sphere><radius>{size[0]:.4f}</radius></sphere></geometry>"
    raise ValueError(shape)


def part(name, shape, size, pose, rgb, collide=True, emissive=None):
    """One visual (and optional collision) element inside a link."""
    x, y, z, yaw = pose
    p = f"<pose>{x:.4f} {y:.4f} {z:.4f} 0 0 {yaw:.4f}</pose>"
    g = geometry(shape, size)
    text = f'<visual name="{name}_v">{p}{g}{material(rgb, emissive)}</visual>'
    if collide:
        text += f'<collision name="{name}_c">{p}{g}</collision>'
    return text


def static_model(name, parts, x=0.0, y=0.0, yaw=0.0):
    body = "\n".join(parts)
    return (f'<model name="{name}"><static>true</static>'
            f"<pose>{x:.4f} {y:.4f} 0 0 0 {yaw:.4f}</pose>"
            f'<link name="link">\n{body}\n</link></model>')


ORANGE = (1.0, 0.45, 0.0)
WHITE = (0.95, 0.95, 0.95)
BLACK = (0.08, 0.08, 0.08)


def cone_parts(prefix="cone"):
    """A traffic cone from three stacked cylinders, about 0.3 m tall."""
    return [
        part(f"{prefix}_base", "box", (0.2, 0.2, 0.03), (0, 0, 0.015, 0), ORANGE),
        part(f"{prefix}_low", "cylinder", (0.07, 0.12), (0, 0, 0.09, 0), ORANGE),
        part(f"{prefix}_band", "cylinder", (0.055, 0.06), (0, 0, 0.18, 0), WHITE),
        part(f"{prefix}_top", "cylinder", (0.04, 0.09), (0, 0, 0.255, 0), ORANGE),
    ]


def drop_cone_sdf(name="race_cone"):
    """A cone that falls onto the track. Heavy and wide so it lands upright."""
    body = "\n".join(cone_parts(name))
    return (f'<?xml version="1.0"?><sdf version="1.6"><model name="{name}">'
            f'<link name="link"><inertial><pose>0 0 0.06 0 0 0</pose><mass>3.0</mass>'
            f"<inertia><ixx>0.02</ixx><iyy>0.02</iyy><izz>0.02</izz>"
            f"<ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia></inertial>\n"
            f"{body}\n</link></model></sdf>")


def tyre_stack_parts(prefix, count=3):
    out = []
    for i in range(count):
        out.append(part(f"{prefix}_t{i}", "cylinder", (0.13, 0.09),
                        (0, 0, 0.045 + 0.09 * i, 0), BLACK))
        out.append(part(f"{prefix}_s{i}", "cylinder", (0.131, 0.012),
                        (0, 0, 0.045 + 0.09 * i, 0), WHITE, collide=False))
    return out


def spectator_parts(prefix, x, y, z, rgb):
    """Cylinder body with a sphere head."""
    return [
        part(f"{prefix}_body", "cylinder", (0.045, 0.16), (x, y, z + 0.08, 0), rgb, collide=False),
        part(f"{prefix}_head", "sphere", (0.04,), (x, y, z + 0.2, 0), (0.85, 0.7, 0.55), collide=False),
    ]


def wall_ring(prefix, centres_and_yaws, length, thickness, height, colours):
    out = []
    for i, (x, y, yaw, seg_len) in enumerate(centres_and_yaws):
        rgb = colours[i % len(colours)]
        out.append(part(f"{prefix}{i}", "box", (seg_len, thickness, height),
                        (x, y, height / 2, yaw), rgb))
    return out


def stadium_outline(straight_length, radius, arc_step_deg, block_length):
    """Wall block centres (x, y, yaw, length) around a stadium of this radius."""
    half = straight_length / 2.0
    blocks = []
    n_straight = max(1, round(straight_length / block_length))
    seg = straight_length / n_straight
    for sign in (-1, 1):
        for i in range(n_straight):
            x = -half + seg * (i + 0.5)
            blocks.append((x, sign * radius, 0.0, seg))
    step = math.radians(arc_step_deg)
    n_arc = max(1, round(math.pi / step))
    step = math.pi / n_arc
    chord = 2 * radius * math.sin(step / 2) + 0.01
    for cx, a0 in ((half, -math.pi / 2), (-half, math.pi / 2)):
        for i in range(n_arc):
            a = a0 + step * (i + 0.5)
            x = cx + radius * math.cos(a) * math.cos(step / 2)
            y = radius * math.sin(a) * math.cos(step / 2)
            blocks.append((x, y, a + math.pi / 2, chord))
    return blocks
