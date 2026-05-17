# Missions

Autonomous missions for Autobot.

## Bottle Hunt

The `bottle_hunt_mission` node searches for a bottle, centers it in the
camera image, approaches it, and stops when it is close enough. It uses:

- `/bottle_target` from `autobot_drivers/bottle_detector`
- `/cmd_vel` to drive through `motor_driver`
- Yahboom ultrasonic range as an extra stop condition

Run the normal robot bringup first:

```bash
ros2 launch autobot_drivers bringup.launch.py
```

Close the browser teleop page before starting the mission. The page publishes
`/cmd_vel` while connected, which can override the autonomous commands.

Then run the mission in another terminal:

```bash
ros2 launch missions bottle_hunt.launch.py
```

If a detector is already running:

```bash
ros2 launch missions bottle_hunt.launch.py start_detector:=false
```

Useful camera streams:

```text
http://<pi-ip>:8080/stream?topic=/image_raw
http://<pi-ip>:8080/stream?topic=/image_annotated
```
