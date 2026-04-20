from setuptools import find_packages, setup

package_name = 'autobot_drivers'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='autobot',
    maintainer_email='you@example.com',
    description='Low-level hardware drivers for Autobot',
    license='MIT',
    entry_points={
        'console_scripts': [
            'motor_driver = autobot_drivers.motor_driver_node:main',
            'bottle_detector = autobot_drivers.bottle_detector_node:main',
            'teleop = autobot_drivers.teleop_node:main',
            'joy_teleop = autobot_drivers.joy_teleop_node:main',
        ],
    },
)
