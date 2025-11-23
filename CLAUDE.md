# CLAUDE.md - AGV Master Codebase Guide

This document provides comprehensive guidance for AI assistants working with the AGV Master codebase.

## Project Overview

**AGV Master** is a ROS (Robot Operating System) package for autonomous navigation of a Jetson Nano-based UGV (Unmanned Ground Vehicle) - specifically the Jetracer platform. The system implements autonomous navigation using:

- OccupancyGrid mapping
- A* pathfinding algorithm
- Pure Pursuit and Stanley controllers
- Marvelmind indoor GPS for localization
- IMU for orientation sensing
- YOLO-based person detection (darknet_ros)

**Target Platform**: Jetson Nano running ROS (Kinetic/Melodic/Noetic compatible)

## Repository Structure

```
agv_master/
├── CMakeLists.txt          # ROS catkin build configuration
├── package.xml             # ROS package metadata and dependencies
├── README.md               # User-facing documentation
├── agv_master.gif          # Demo visualization
├── scripts/                # Python scripts (main logic)
│   ├── agv_node.py        # Primary ROS node (385 lines)
│   └── library_agv.py     # Data classes (AGV, Person, Map)
├── src/                    # C++ source files (currently empty)
├── include/                # C++ header files (currently empty)
│   └── agv_master/
├── rviz/                   # RViz visualization configs
│   └── display_agv.rviz   # Pre-configured visualization layout
└── .git/                   # Git repository metadata
```

### Directory Purposes

- **scripts/**: Contains all executable Python code for the AGV logic
- **src/**: Reserved for C++ implementations (currently unused)
- **include/**: Reserved for C++ headers (currently unused)
- **rviz/**: Contains visualization configurations for debugging and monitoring

## Core Components

### 1. Main Node (`scripts/agv_node.py`)

The primary ROS node that orchestrates all AGV functionality.

**Key Functions**:

- `initialize_map()` - Creates 600x360 OccupancyGrid at 1cm resolution (lines 41-62)
- `initialize_yaw()` - Calibrates IMU yaw offset on startup (lines 152-161)
- `listener()` - Main control loop running at 20Hz (lines 114-150)
- `a_star()` - Simplified A* pathfinding implementation (lines 206-232)
- `pure_pursuit()` - Primary path tracking controller (lines 234-254)
- `stanley()` - Alternative Stanley controller (lines 256-275)
- `update_goal()` - Goal management and scoring logic (lines 277-287)

**Callback Functions**:
- `callback_update_pos()` - Processes Marvelmind beacon positions (lines 163-174)
- `callback_update_yaw()` - Processes IMU orientation data (lines 176-183)
- `callback_update_person_pos()` - Processes YOLO person detections (lines 185-193)

### 2. Data Classes (`scripts/library_agv.py`)

**AGV Class** (lines 5-24):
- Position: `x`, `y` (fused from two Marvelmind beacons)
- Raw beacon readings: `x1`, `y1`, `x2`, `y2`
- Orientation: `yaw`, `yaw_offset`
- Control: `steering_angle`

**Person Class** (lines 27-35):
- Position: `x`, `y`
- Detection flag: `detected` (0/1)

**Map Class** (lines 38-58):
- Grid data: `data` (OccupancyGrid), `initial_data`
- Resolution: `res` (0.01m = 1cm)
- Goal: `goal_x`, `goal_y`
- Path: `path` (2x1000 numpy array)
- Lookahead point: `p_x`, `p_y`
- Score tracking: `score`

## ROS Communication

### Published Topics

| Topic | Type | Purpose | Rate |
|-------|------|---------|------|
| `/map` | `OccupancyGrid` | Current occupancy grid map | 20Hz |
| `/ego_pose` | `Float32MultiArray` | AGV position [x, y] | 20Hz |
| `/ego_yaw` | `Float32` | AGV heading in degrees | 20Hz |
| `/path` | `Float32MultiArray` | Lookahead point coordinates | 20Hz |
| `/steering_angle` | `Float32` | Steering angle in radians | 20Hz |
| `/steering_` | `Float32` | Steering angle in degrees | 20Hz |
| `/visual` | `PointCloud` | Path visualization (166 points) | 20Hz |
| `/marker_goal` | `Marker` | Goal position marker (red cube) | 20Hz |
| `/marker_car` | `Marker` | Vehicle marker (green cube) | 20Hz |
| `/marker_direction` | `Marker` | Steering direction arrow (blue) | 20Hz |

### Subscribed Topics

| Topic | Type | Purpose | Source |
|-------|------|---------|--------|
| `/hedge_pos_ang` | `hedge_pos_ang` | Beacon positions | Marvelmind GPS |
| `/darknet_ros/bounding_boxes` | `BoundingBoxes` | Person detection | YOLO/Darknet |
| `/imu` | `Imu` | Orientation data | E2BOXIMU 9DOFv5 |

## Key Algorithms

### A* Pathfinding (`a_star()`, lines 206-232)

**Implementation**: Simplified greedy A* that generates 166 waypoints

**Algorithm**:
1. Start from current AGV position
2. For each of 166 iterations:
   - Check 3x3 grid around current position
   - Calculate cost: `distance_to_goal + occupancy_value * distance_to_goal`
   - Select minimum cost cell
   - Add to path array

**Cost Function**: `f = h + h * occupancy`
- `h`: Euclidean distance to goal
- Occupancy multiplier penalizes obstacles (0-100 values)

**Note**: This is NOT a full A* implementation - it's a greedy local planner with obstacle avoidance.

### Pure Pursuit Controller (`pure_pursuit()`, lines 234-254)

**Parameters**:
- Lookahead distance: `1.1 * 0.5 * (1/res)` = 55cm preview distance
- Wheelbase: `0.15 * (1/res)` = 15cm
- Reference point: Rear axle center

**Algorithm**:
1. Calculate rear axle position relative to vehicle heading
2. Find path point closest to lookahead distance
3. Calculate steering angle: `δ = arctan(2 * L * sin(α) / ld)`
   - `L`: wheelbase
   - `α`: angle between heading and lookahead point
   - `ld`: lookahead distance

### Stanley Controller (`stanley()`, lines 256-275)

**Parameters**:
- Gain: `k = 0.5`
- Velocity: `v = 0.7` m/s (approximate)
- Softening constant: `k_s = 0.000001`

**Algorithm**:
1. Find closest path point to front axle
2. Calculate heading error from path tangent
3. Calculate cross-track error term: `arctan(k * e / (k_s + v))`
4. Steering = heading_error + crosstrack_error

**Note**: Currently commented out in favor of Pure Pursuit (line 144).

## Hardware Configuration

### Coordinate System

- **Origin**: Map frame at (0, 0)
- **Units**: Meters
- **Axes**: Standard ROS convention (X forward, Y left, Z up)

### Sensor Setup

**Marvelmind Beacons**:
- Two beacons mounted on vehicle (addresses 12 and 13)
- Beacon 12: Left position (`x1`, `y1`)
- Beacon 13: Right position (`x2`, `y2`)
- Vehicle center calculated as midpoint + heading offset (line 172)

**IMU**:
- E2BOXIMU 9DOFv5 connected to UART (ttyTHS1)
- Provides yaw angle in `orientation.x` field
- Requires calibration offset on initialization

**Camera** (optional):
- Uses darknet_ros for YOLO object detection
- Currently only detects "person" class
- Fixed obstacle position when detected (line 190-191)

## Code Conventions

### Python Style

- **Shebang**: `#!/usr/bin/env python` (Python 2/3 compatible)
- **Imports**: Standard library → ROS → third-party → local
- **Naming**:
  - Functions: `snake_case`
  - Classes: `PascalCase`
  - Constants: module-level class attributes
  - Private variables: suffix with underscore (e.g., `res_`, `yaw_`)

### ROS Conventions

- **Node name**: `AGV_node` (line 378)
- **Publishers**: Declared globally, prefixed `pub_` (lines 25-38)
- **Queue size**: 10 for data topics
- **Latching**: Enabled for most topics (state information)
- **Rate**: 20Hz main loop (line 119)

### Coordinate Transformations

- **Angular units**: Degrees for yaw storage, radians for calculations
- **Conversion**: Use `np.deg2rad()` and `np.rad2deg()` explicitly
- **Map coordinates**: Pixels to meters via `Map.res` (0.01m/pixel)

## Development Workflows

### Building the Package

```bash
cd ~/catkin_ws/src
git clone <repository_url> agv_master
cd ~/catkin_ws
catkin_make
source devel/setup.bash
```

### Running the System

**Prerequisites**:
1. Marvelmind beacons configured and publishing
2. IMU connected and accessible at `/dev/ttyTHS1`
3. ROS master running on ground control station
4. Network configuration set in `.bashrc`

**Launch**:
```bash
# On Jetson Nano
rosrun agv_master agv_node.py

# On ground control station (for visualization)
rviz -d ~/catkin_ws/src/agv_master/rviz/display_agv.rviz
```

### Testing Without Hardware

**Mocking sensors**: Create test publishers for `/hedge_pos_ang` and `/imu`

```bash
# Example: Publish static IMU data
rostopic pub /imu sensor_msgs/Imu '{orientation: {x: 0.0, y: 0, z: 0, w: 1}}'
```

## Common AI Assistant Tasks

### 1. Adding New Obstacles

**Location**: `listener()` function, after line 136

**Pattern**:
```python
# Static obstacle example (lines 138-141)
for i in range(x_start, x_end):
    for j in range(y_start, y_end):
        np_map[j, i] = 99  # High occupancy value
```

**Units**: `i`, `j` are in pixels (multiply meters by `1/Map.res`)

### 2. Tuning Controllers

**Pure Pursuit**:
- Lookahead: Line 236 (`ld = 1.1 * 0.5 * res_`)
- Wheelbase: Line 237 (`wheel_base = 0.15 * res_`)

**Stanley**:
- Gain: Line 265 (`k = 0.5`)
- Velocity: Line 266 (`v = 0.7`)

### 3. Modifying Goal Behavior

**Location**: `update_goal()` function (lines 277-287)

**Current logic**:
- Triggers when within 0.3m of goal (line 280)
- Generates random goal in bounds [1m, 5m] x [1m, 3m]
- Shuts down after 5 goals reached

### 4. Adding New ROS Topics

**Pattern**:
1. Import message type at top of file
2. Declare publisher globally: `pub_name = rospy.Publisher(...)`
3. Create and publish message in `talker()` function

**Example** (lines 25-38 for reference):
```python
pub_new_topic = rospy.Publisher('/topic_name', MessageType, latch=True, queue_size=10)

# In talker():
msg = MessageType()
msg.data = value
pub_new_topic.publish(msg)
```

### 5. Debugging Visualization

**RViz Configuration** (`rviz/display_agv.rviz`):
- Map: OccupancyGrid display (70% transparency)
- Path: PointCloud of 166 waypoints
- Markers: Goal (red), vehicle (green), steering direction (blue)
- Fixed frame: `map`
- View: Top-down orthographic

**Adding new markers**: See `update_marker_*()` functions (lines 298-373)

## Dependencies

### ROS Packages
- `roscpp`, `rospy`: Core ROS libraries
- `std_msgs`: Standard message types
- `nav_msgs`: Navigation messages (OccupancyGrid)
- `geometry_msgs`: Pose and point messages
- `sensor_msgs`: IMU and PointCloud messages
- `visualization_msgs`: Marker messages
- `marvelmind_nav`: Marvelmind GPS interface
- `darknet_ros_msgs`: YOLO detection messages

### Python Packages
- `numpy`: Numerical operations and array handling
- `rospy`: ROS Python client library
- Built-in: `time`, `sys`, `copy`

## Troubleshooting

### Common Issues

**1. IMU Initialization Fails** (line 159)
- Check `/dev/ttyTHS1` permissions: `sudo chmod 666 /dev/ttyTHS1`
- Verify IMU is publishing valid data: `rostopic echo /imu`
- Ensure `orientation.x >= 0` check passes

**2. No Marvelmind Data**
- Verify beacons are configured with addresses 12 and 13
- Check topic: `rostopic echo /hedge_pos_ang`
- Confirm Dashboard software settings

**3. Path Not Updating**
- Check map resolution matches `Map.res = 0.01`
- Verify goal is within map bounds (600x360 pixels = 6x3.6m)
- Examine occupancy grid for blocked paths

**4. Vehicle Not Moving**
- Steering angle published to `/steering_angle` (radians)
- Verify Jetracer node is subscribed and processing commands
- Check network configuration (ROS_MASTER_URI, ROS_IP)

## Performance Considerations

### Computational Bottlenecks

1. **A* Pathfinding** (line 206): O(166 * 9) = ~1500 operations per cycle
2. **Occupancy Updates** (line 195): O(area) for person detection
3. **PointCloud Publishing** (line 95): 166 points per message

**Optimization opportunities**:
- Reduce path resolution (currently 166 points)
- Implement proper A* with priority queue
- Cache map regions that don't change

### Real-time Performance

- **Main loop**: 20Hz (50ms period)
- **Critical path**: Callbacks → Map update → A* → Controller → Publish
- **Latency budget**: Must complete within 50ms for stable control

## Architecture Decisions

### Why Python for Control?

- ROS integration simplicity
- Rapid prototyping for research
- NumPy efficiency for array operations
- Adequate performance for 20Hz control loop

### Why Two Marvelmind Beacons?

- Single beacon provides position only
- Two beacons enable heading calculation
- Fusion with IMU improves accuracy (line 172)

### Why Simplified A*?

- Full A* overhead unnecessary for simple environments
- Greedy approach sufficient with 1cm resolution
- 20Hz update rate allows reactive replanning

## Future Improvements

### Suggested Enhancements

1. **Full A* Implementation**: Priority queue, proper open/closed sets
2. **Dynamic Reconfigure**: Runtime parameter tuning without code changes
3. **Launch Files**: Automated startup of dependencies
4. **Velocity Control**: Currently only steering is commanded
5. **Multi-goal Missions**: Waypoint sequences instead of random goals
6. **Logging**: rosbag recording for post-analysis
7. **Unit Tests**: Validation of controller and pathfinding logic

### Code Quality

- **Type hints**: Add for Python 3 compatibility
- **Docstrings**: Document all functions with parameters and return types
- **Error handling**: Add try/except blocks for sensor failures
- **Configuration file**: Extract magic numbers to YAML config

## Git Workflow

### Branching Strategy

- **Main branch**: Stable, tested code
- **Feature branches**: `claude/*` prefix for AI-assisted development
- **Naming**: `claude/claude-md-<session-id>-<feature-name>`

### Commit Messages

**Format**:
```
<type>: <brief description>

<detailed explanation if needed>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code restructuring
- `docs`: Documentation only
- `tune`: Parameter adjustments
- `test`: Testing additions

### Development Workflow

1. Create feature branch from main
2. Make changes with clear commits
3. Test with actual or simulated hardware
4. Push to feature branch
5. Create pull request for review

## Contact and Resources

### External Dependencies

- **Jetracer setup**: https://github.com/mych907/cytron_jetracer
- **Marvelmind ROS**: https://github.com/MarvelmindRobotics/marvelmind_nav-release
- **Marvelmind docs**: https://marvelmind.com/pics/marvelmind_ROS.pdf
- **E2BOX IMU**: https://github.com/mych907/e2box_imu_9dofv5

### ROS Resources

- **ROS Wiki**: http://wiki.ros.org/
- **nav_msgs/OccupancyGrid**: http://docs.ros.org/api/nav_msgs/html/msg/OccupancyGrid.html
- **geometry_msgs**: http://docs.ros.org/api/geometry_msgs/html/index-msg.html

## Quick Reference

### File Locations

- Main node: `scripts/agv_node.py`
- Data classes: `scripts/library_agv.py`
- RViz config: `rviz/display_agv.rviz`
- Build config: `CMakeLists.txt`, `package.xml`

### Key Parameters

- Map size: 600x360 pixels (6m x 3.6m)
- Map resolution: 0.01m (1cm/pixel)
- Control frequency: 20Hz
- Lookahead distance: 55cm
- Wheelbase: 15cm
- Goal threshold: 0.3m

### Important Line Numbers

- Map initialization: 41-62
- Main loop: 114-150
- A* algorithm: 206-232
- Pure Pursuit: 234-254
- Callbacks: 163-193

---

**Last Updated**: 2025-11-23
**Codebase Version**: Based on commit `1a71f38`
