import gym
from gym import error, spaces, utils
from gym.utils import seeding

from gym_match3.envs.game import Game, Point
from gym_match3.envs.game import OutOfBoardError, ImmovableShapeError
from gym_match3.envs.levels import LEVELS, Match3Levels
from gym_match3.envs.renderer import Renderer

from itertools import product
import warnings
import numpy as np

BOARD_NDIM = 2


class Match3Env(gym.Env):
    metadata = {'render.modes': True}

    def __init__(self, rollout_len=100, all_moves=False, levels=None, random_state=None):
        self.rollout_len = rollout_len
        self.random_state = random_state
        self.all_moves = all_moves
        self.levels = levels or Match3Levels(LEVELS)
        self.h = self.levels.h
        self.w = self.levels.w
        self.n_shapes = self.levels.n_shapes
        self.__episode_counter = 0

        self.__game = Game(
            rows=self.h,
            columns=self.w,
            n_shapes=self.n_shapes,
            length=3,
            all_moves=all_moves,
            random_state=self.random_state)
        self.reset()[np.newaxis,:]
        self.renderer = Renderer(self.n_shapes)

        # setting observation space
        self.observation_space = spaces.Box(
            low=0,
            high=self.n_shapes,
            #shape=self.__game.board.board_size,
            shape=(1,self.h,self.w),
            dtype=int)

        # setting actions space
        self.__match3_actions = self.get_available_actions()
        self.action_space = spaces.Discrete(
            len(self.__match3_actions))

    @staticmethod
    def get_directions(board_ndim):
        """ get available directions for any number of dimensions """
        directions = [
            [[0 for _ in range(board_ndim)] for _ in range(2)]
            for _ in range(board_ndim)
        ]
        for ind in range(board_ndim):
            directions[ind][0][ind] = 1
            directions[ind][1][ind] = -1
        return directions

    def points_generator(self):
        """ iterates over points on the board """
        rows, cols = self.__game.board.board_size
        points = [Point(i, j) for i, j in product(range(rows), range(cols))]
        for point in points:
            yield point

    def get_available_actions(self):
        """ calculate available actions for current board sizes """
        actions = set()
        directions = self.get_directions(board_ndim=BOARD_NDIM)
        for point in self.points_generator():
            for axis_dirs in directions:
                for dir_ in axis_dirs:
                    dir_p = Point(*dir_)
                    new_point = point + dir_p
                    try:
                        _ = self.__game.board[new_point]
                        actions.add(frozenset((point, new_point)))
                    except OutOfBoardError:
                        continue
        return list(actions)

    def get_action(self, ind):
        return self.__match3_actions[ind]

    def step(self, action):
        # make action
        m3_action = self.get_action(action)
        reward = self.swap(*m3_action)

        # change counter even action wasn't successful
        self.__episode_counter += 1
        if self.__episode_counter >= self.rollout_len:
            episode_over = True
            self.__episode_counter = 0
            #ob = self.reset()
            ob = self.get_board()[np.newaxis,:]
        else:
            episode_over = False
            ob = self.get_board()[np.newaxis,:]

        return ob, reward, episode_over, {}

    def reset(self, *args, **kwargs):
        board = self.levels.sample()
        self.__game.start(board)
        return self.get_board()[np.newaxis,:]

    def swap(self, point1, point2):
        try:
            reward = self.__game.swap(point1, point2)
        except ImmovableShapeError:
            reward = 0
        return reward

    def get_board(self):
        return self.__game.board.board.copy()

    def render(self, mode='human', close=False):
        if close:
            warnings.warn("close=True isn't supported yet")
        self.renderer.render_board(self.__game.board)