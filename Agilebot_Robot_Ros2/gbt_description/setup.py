from setuptools import find_packages, setup
from glob import glob
import os

package_name = 'gbt_description'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # meshes visual files
        (os.path.join('share', package_name, 'meshes','visual'), glob(os.path.join('meshes', 'visual', '*'))),
        # meshes collision files
        (os.path.join('share', package_name, 'meshes','collision'), glob(os.path.join('meshes', 'collision', '*'))),
        # urdf files    
        (os.path.join('share', package_name, 'urdf'), glob(os.path.join('urdf', '*'))),
        # luanch files
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*'))),
        # config files  
        (os.path.join('share', package_name, 'config'), glob(os.path.join('config', '*'))),
        # rviz files
        (os.path.join('share', package_name, 'rviz'), glob(os.path.join('rviz', '*'))),

    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='lidesheng',
    maintainer_email='lidesheng@agilebot.com.cn',
    description='The gbt_description is a ROS 2 package used for describing robot models. The package contains URDF (Unified Robot Description Format) files, related 3D models, and configuration files. It can be loaded by other components in ROS 2 (such as MoveIt2, Gazebo, etc.) for tasks such as simulation, planning, and control.',
    license='BSD-3-Clause',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
        ],
    },
)
