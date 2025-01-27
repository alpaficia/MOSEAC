import gymnasium as gym
from gymnasium import spaces
from envs.Acceleration_simulation import AccelerationSimulator
import pygame
import numpy as np
import math


def coordinate_system_conversion(coordinate):
    origin_coordinate = np.array([1.0, 1.0])
    target_coordinate_x = origin_coordinate[0] + coordinate[0]
    target_coordinate_y = origin_coordinate[1] - coordinate[1]
    target_coordinate_x = max(0.0, target_coordinate_x)
    target_coordinate_x = min(2.0, target_coordinate_x)
    target_coordinate_y = max(0.0, target_coordinate_y)
    target_coordinate_y = min(2.0, target_coordinate_y)
    return np.array([target_coordinate_x, target_coordinate_y])


def distance(point1, point2):
    return np.linalg.norm(point1 - point2)


def sigmoid(x, k, x0):
    return 1 / (1 + math.exp(-k * (x - x0)))


def calculate_alpha_values(alpha_ori, alpha):
    """
    计算校正后的alpha_t和alpha_tau，确保在alpha=0.12时为1，并符合递增递减要求。

    参数:
    - alpha: 输入的alpha值，可以是单个数值或numpy数组
    - k_t, m_t, scale_t, offset_t: 控制alpha_t sigmoid函数的斜率、偏移、缩放和偏移量
    - k_tau, n_tau, scale_tau, offset_tau: 控制alpha_tau sigmoid函数的斜率、偏移、缩放和偏移量

    返回:
    - alpha_t: 计算后的alpha_t值
    - alpha_tau: 计算后的alpha_tau值
    """
    # 调整参数以确保在alpha=0.12时，alpha_t和alpha_tau都为1
    k_t = 10  # 负斜率，使得alpha_t随alpha增大而减小
    m_t = alpha_ori  # sigmoid中心偏移至0.12
    scale_t = 1  # 调整尺度使得最大值为1
    offset_t = 0  # 基础偏移量

    k_tau = 10  # 正斜率，使得alpha_tau随alpha增大而增加
    n_tau = alpha_ori  # sigmoid中心偏移至0.12
    scale_tau = 1  # 调整尺度使得最大值为1
    offset_tau = 0  # 基础偏移量
    alpha_t = scale_t * (1 - sigmoid(k_t * (alpha - m_t))) + offset_t
    alpha_tau = scale_tau * sigmoid(k_tau * (alpha - n_tau)) + offset_tau
    return 2 * alpha_t, 2 * alpha_tau


class DynamicWorldNDEnv(gym.Env):
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 4}

    def __init__(self, render_mode=None, size=2.0):
        self._target_location = None  # target location info, in (x, y)
        self._obstacle_location = None  # obstacle location info, in (x, y)
        self._agent_location = None  # agent location info, in (x, y)
        self._agent_old_speed = np.zeros(2,)  # in m/s
        self.agent_new_speed = np.zeros(2,)  # in m/s
        self.judgment_distance = 0.05  # in meters
        self.time_step_duration = np.zeros(1,)
        self.force = np.zeros(2,)
        self.reset_mark = False  # if the env get reset, set this mark to True to clean some history data
        self.size = size  # The size of the pygame square world
        self.window_size = 512  # The size of the PyGame window
        self.weather_info = 3.0  # weather, from 0.0 to 3.0, 0.0 present sunny, details see Acceleration_simulation.py
        self.max_force = 6  # maximum movement per step, in meters
        self.max_speed = 2.0  # maximum speed of the agent in m/s
        self.gain = 1.0  # the gain factor for the reward parts on finished task
        self.gain_eps = 0.1
        self.min_time = 0.01
        self.max_time = 1.0
        self.original_dis = np.nan
        self.time_buffer = np.zeros(1,)  # a buffer to cumulate time for reward
        self.observation_space = spaces.Dict(
            {
                "agent_pos": spaces.Box(-1.0, 1.0, shape=(2,), dtype=np.float64),
                "obstacle": spaces.Box(-1.0, 1.0, shape=(2,), dtype=np.float64),
                "target": spaces.Box(-1.0, 1.0, shape=(2,), dtype=np.float64),
                "speed": spaces.Box(-2.0, 2.0, shape=(2,), dtype=np.float64),
                "time": spaces.Box(0.0, 1.0, shape=(1,), dtype=np.float64),
                "force": spaces.Box(-100.0, 100.0, shape=(2,), dtype=np.float64),
            }
        )

        self.action_space = spaces.Box(low=-1.0 * self.max_force, high=self.max_force, shape=(4,))
        self.dynamic_simulator = AccelerationSimulator(weather_info=self.weather_info,
                                                       max_speed=self.max_speed)  # Newton's force simulation

        assert render_mode is None or render_mode in self.metadata["render_modes"]
        self.render_mode = render_mode

        """
        If human-rendering is used, `self.window` will be a reference
        to the window that we draw to. `self.clock` will be a clock that is used
        to ensure that the environment is rendered at the correct frame rate in
        human-mode. They will remain `None` until human-mode is used for the
        first time.
        """
        self.window = None
        self.clock = None

    def _get_obs(self):
        return {"agent_pos": self._agent_location, "obstacle": self._obstacle_location, "target": self._target_location,
                "speed": self.agent_new_speed, "time": self.time_step_duration, "force": self.force}

    def _get_info(self):
        return {
            "distance_2_goal": np.linalg.norm(self._agent_location - self._target_location, ord=2),
            "distance_2_obstacle": np.linalg.norm(self._agent_location - self._obstacle_location, ord=2)
        }

    def reset(self, seed=None, options=None):
        # We need the following line to seed self.np_random
        super().reset(seed=seed)
        self.time_step_duration = np.zeros(1,)  # reset the time of one time step
        self.time_buffer = np.zeros(1, )  # reset the cumulative time buffer
        self.force = np.zeros(2, )  # reset the records of true movement
        # Choose the agent's location uniformly at random
        self._agent_location = self.np_random.uniform(-1.0, 1.0, size=2)
        # We will sample the target's location randomly until it does not coincide with the agent's location
        self._target_location = self._agent_location
        self._obstacle_location = self._agent_location
        while np.linalg.norm(self._target_location - self._agent_location, ord=2) <= self.judgment_distance:
            self._target_location = self.np_random.uniform(-1.0, 1.0, size=2)
        while np.linalg.norm(self._obstacle_location - self._agent_location, ord=2) <= self.judgment_distance or \
                np.linalg.norm(self._obstacle_location - self._target_location, ord=2) <= self.judgment_distance:
            self._obstacle_location = self.np_random.uniform(-1.0, 1.0, size=2)
        self.original_dis = distance(self._agent_location, self._target_location)
        ###########################################################################################################

        observation = self._get_obs()
        self._agent_old_speed = np.zeros([2, ])
        info = self._get_info()
        self.reset_mark = True

        if self.render_mode == "human":
            self._render_frame()

        return observation, info

    def step(self, action):
        action_time = np.array(action[0])  # the time for current action
        action_force = np.array(action[1:3])  # the move distance for current action, vector
        last_step = action[-1]
        # if it is the last time for whole epoch, if true, agent will continue move in the same direction till stop
        reset = self.reset_mark  # checkout if the env got reset
        self.time_step_duration = np.array([action_time])
        true_move, true_new_speed = self.dynamic_simulator.compute_actual_movement_and_speed(self.time_step_duration,
                                                                                             action_force, last_step,
                                                                                             reset)
        self.force = action_force
        if reset:
            self.reset_mark = False
        self._agent_location += true_move  # simulated movement
        self.agent_new_speed = true_new_speed
        self._agent_old_speed = true_new_speed  # updated the history speed
        self._agent_location = np.clip(self._agent_location, -1.0, 1.0)
        # We use `np.clip` to make sure we don't leave the world
        self.time_buffer += self.time_step_duration
        observation = self._get_obs()
        # An episode is done iff the agent has reached the target
        if np.linalg.norm(self._agent_location - self._target_location) <= self.judgment_distance:
            reward = 500.0
            terminated = True
        elif np.linalg.norm(self._agent_location - self._obstacle_location) <= self.judgment_distance:
            reward = -500.0
            terminated = True
        else:
            reward_task = self.original_dis - distance(self._agent_location, self._target_location)
            reward_time = self.reward_time_remapping(action_time)
            reward = self.gain * (reward_task * reward_time - self.gain_eps)
            terminated = False
        #  We compute the reward based on three different considerations, that is being explained within our paper

        info = self._get_info()
        if self.render_mode == "human":
            self._render_frame()
        return observation, float(reward), terminated, False, info

    # def update_gain(self, alpha_ori, alpha):
    #     self.gain_task, self.gain_speed = calculate_alpha_values(alpha_ori, alpha)

    def update_gain_r(self, increase_amount):
        # 更新 self.gain
        self.gain += increase_amount
        # 使用逆向 Sigmoid 函数更新 self.gain_eps
        # 选择k和x0的值以确保在gain为1时gain_eps为0.1
        k = 1  # 控制sigmoid函数的斜率
        x0 = 1  # 控制sigmoid中心为1，使得gain为1时输出特定值
        # 更新self.gain_eps，将sigmoid输出乘以10，并减去1使得gain为1时gain_eps为0.1
        self.gain_eps = 0.2 * (1 - sigmoid(self.gain, k, x0))

    def reward_time_remapping(self, reward):
        reward_t = self.min_time / reward
        return reward_t

    def render(self):
        if self.render_mode == "rgb_array":
            return self._render_frame()

    def _render_frame(self):
        if self.window is None and self.render_mode == "human":
            pygame.init()
            pygame.display.init()
            self.window = pygame.display.set_mode((self.window_size, self.window_size))
        if self.clock is None and self.render_mode == "human":
            self.clock = pygame.time.Clock()

        canvas = pygame.Surface((self.window_size, self.window_size))
        canvas.fill((255, 255, 255))
        pix_square_size = (
                self.window_size / self.size
        )  # The size of a single world square in pixels
        if self.weather_info == 0.0:
            weather_text = "Sunny"
        elif self.weather_info == 1.0:
            weather_text = "Rain"
        elif self.weather_info == 2.0:
            weather_text = "Snow"
        elif self.weather_info == 3.0:
            weather_text = "Ice"
        else:
            weather_text = "Unknown"
        font = pygame.font.SysFont("freesansbold.ttf", 30)
        text_agent = font.render("Agent", True, (0, 0, 255))
        text_goal = font.render("Goal", True, (255, 0, 0))
        text_obs = font.render("Obs", True, (0, 255, 0))
        text_weather = font.render(weather_text, True, (0, 0, 0))
        # First we draw the target
        pygame.draw.rect(
            canvas,
            (255, 0, 0),
            pygame.Rect(
                pix_square_size * coordinate_system_conversion(self._target_location),
                (pix_square_size / 10, pix_square_size / 10),
            ),
        )
        # then we draw the obstacle
        pygame.draw.rect(
            canvas,
            (0, 255, 0),
            pygame.Rect(
                pix_square_size * coordinate_system_conversion(self._obstacle_location),
                (pix_square_size / 10, pix_square_size / 10),
            ),
        )
        # Now we draw the agent
        pygame.draw.circle(
            canvas,
            (0, 0, 255),
            coordinate_system_conversion(self._agent_location) * pix_square_size,
            pix_square_size / 15,
        )

        if self.render_mode == "human":
            # The following line copies our drawings from `canvas` to the visible window
            self.window.blit(canvas, canvas.get_rect())
            self.window.blit(text_agent, (450, 10))
            self.window.blit(text_goal, (450, 30))
            self.window.blit(text_obs, (450, 50))
            self.window.blit(text_weather, (450, 70))
            pygame.event.pump()
            pygame.display.update()

            # We need to ensure that human-rendering occurs at the predefined frame rate.
            # The following line will automatically add a delay to keep the frame rate stable.
            self.clock.tick(self.metadata["render_fps"])
        else:  # rgb_array
            return np.transpose(
                np.array(pygame.surfarray.pixels3d(canvas)), axes=(1, 0, 2)
            )

    def close(self):
        if self.window is not None:
            pygame.display.quit()
            pygame.quit()
