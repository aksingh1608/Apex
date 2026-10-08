from glob import glob

from setuptools import setup

package_name = "apex_race"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.py")),
        ("share/" + package_name + "/config", glob("config/*.yaml") + glob("config/*.rviz")),
        ("share/" + package_name + "/worlds", glob("worlds/*.world")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Aryan Kumar Singh",
    maintainer_email="aksingh5114@gmail.com",
    description="Apex time trial on a generated circuit.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "race_controller_node = apex_race.race_controller_node:main",
            "monitor_node = apex_race.monitor_node:main",
            "keyboard_node = apex_race.keyboard_node:main",
            "drop_obstacle = apex_race.drop_obstacle:main",
        ],
    },
)
