import random
import numpy as np
from enum import Enum
import configparser

class Direction(Enum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3
    STRAIGHT = 4

class Signal(Enum):
    NORMAL = 0
    HIT = 1
    EAT = 2

class GreedySnake:


    def __init__(self):
        config = configparser.ConfigParser()
        config.read('greedysnake.ini')
        env = 'DEFAULT'
        snake_1_init_row = int(config[env]['snake_1_init_row'])
        snake_1_init_col = int(config[env]['snake_1_init_col'])
        snake_2_init_row = int(config[env]['snake_2_init_row'])
        snake_2_init_col = int(config[env]['snake_2_init_col'])
        food_row = int(config[env]['food_row'])
        food_col = int(config[env]['food_col'])
        self.SIZE = int(config[env]['size'])
        self.INIT_SNAKE = [np.array([snake_1_init_row, snake_1_init_col]), np.array([snake_2_init_row, snake_2_init_col])]
        self.INIT_FOOD = np.array([food_row, food_col])
        self.PICK_BLOCKS = list(range(0, self.SIZE*self.SIZE))
        self.snake = self.INIT_SNAKE
        self.food = self.INIT_FOOD
        self.head_direction = Direction.LEFT
        
    def is_snake(self, i, j):
        for k in range(len(self.snake)):
            if (np.array(self.snake[k]) == np.array([i, j])).all():
                return k
        return -1

    def step(self, action = Direction.STRAIGHT):
        
        signal = None
        action_vec = np.array([0, 0])

        if (((self.head_direction == Direction.UP) or (self.head_direction == Direction.DOWN))
            and (action == Direction.UP or action == Direction.DOWN)) or (((self.head_direction == Direction.LEFT) 
            or (self.head_direction == Direction.RIGHT))
            and (action == Direction.LEFT or action == Direction.RIGHT)):
                action = Direction.STRAIGHT

        # set action vector
        if action == Direction.STRAIGHT:
            action = self.head_direction
        if action == Direction.LEFT:
            action_vec = np.array([0, -1])
        elif action == Direction.RIGHT:
            action_vec = np.array([0, 1])
        elif action == Direction.UP:
            action_vec = np.array([-1, 0])
        elif action == Direction.DOWN:
            action_vec = np.array([1, 0])
        else:
            action_vec = np.array([0, 0])

        # set head direction
        self.head_direction = action

        # Calculate head position after the step
        head = self.snake[0] + action_vec

        # Hit the wall
        if head[0] == -1 or head[1] == -1 or head[0] > self.SIZE - 1 or head[1] > self.SIZE - 1:
            signal = Signal.HIT

        # Hit the snake
        elif self.is_snake(head[0], head[1]) != -1:
            signal = Signal.HIT

        # Eat the food
        elif (head == self.food).all():

            # Generate new food on a random position exclude last food and snake positions
            pick_pos = self.PICK_BLOCKS.copy()
            for snake_part in self.snake:
                index = snake_part[0] * self.SIZE + snake_part[1]
                pick_pos.remove(index)
            pick_pos.remove(self.food[0] * self.SIZE + self.food[1])

            # Snake grows
            self.snake.insert(0, np.array(self.food))

            # Set new food
            new_food = random.choice(pick_pos)
            self.food = np.array([new_food // self.SIZE, new_food % self.SIZE])
            signal = Signal.EAT
        
        else:
            # snake move
            P_t = self.snake.copy()
            P_t_add_one = self.snake.copy()
            P_t_add_one[0] = head
            for i in range(len(P_t_add_one)):
                if i >= 1:
                    P_t_add_one[i] = P_t[i] + (P_t[i-1] - P_t[i])
            self.snake = P_t_add_one
            signal = Signal.NORMAL

        if signal == Signal.HIT:
            self.reset()


        return signal

    def reset(self):
        self.snake = self.INIT_SNAKE

        # Generate new food on a random position exclude last food and snake positions
        pick_pos = self.PICK_BLOCKS.copy()
        for snake_part in self.snake:
            index0 = snake_part[0] * self.SIZE + snake_part[1]
            index1 = (snake_part[0] - 1) * self.SIZE + snake_part[1]
            index2 = snake_part[0] * self.SIZE + snake_part[1] - 1
            index3 = (snake_part[0] - 1) * self.SIZE + snake_part[1] - 1
            index4 = (snake_part[0] + 1) * self.SIZE + snake_part[1]
            index5 = snake_part[0] * self.SIZE + snake_part[1] + 1
            index6 = (snake_part[0] + 1) * self.SIZE + snake_part[1] + 1
            try:
                pick_pos.remove(index0)
                pick_pos.remove(index1)
                pick_pos.remove(index2)
                pick_pos.remove(index3)
                pick_pos.remove(index4)
                pick_pos.remove(index5)
                pick_pos.remove(index6)
            except:
                pass

        # Set new food
        if len(pick_pos) == 0:
            self.food = self.INIT_FOOD
        else:
            new_food = random.choice(pick_pos)
            self.food = np.array([new_food // self.SIZE, new_food % self.SIZE])
        self.head_direction = Direction.LEFT

