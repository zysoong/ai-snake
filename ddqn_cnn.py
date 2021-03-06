from greedysnake import GreedySnake, Direction, Signal
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import backend as K
import configparser
import sys
import warnings
from collections import deque
warnings.filterwarnings("ignore")
np.set_printoptions(threshold=sys.maxsize)

class Driver:

    def __init__(self):
        config = configparser.ConfigParser()
        config.read('ddqn_cnn.ini')
        self.env = config['ENV']['env']
        self.greedysnake = GreedySnake()
        self.signal_in = Direction.STRAIGHT
        self.max_epochs = int(config[self.env]['max_epochs'])
        self.max_steps = int(config[self.env]['max_steps'])
        self.batch_size = int(config[self.env]['batch_size'])
        self.memory_size = int(config[self.env]['memory_size'])
        self.mini_batch_size = int(config[self.env]['mini_batch_size'])
        self.critic_net_epochs = int(config[self.env]['critic_net_epochs'])
        self.gamma = float(config[self.env]['gamma'])
        self.epsilon_init = float(config[self.env]['epsilon_init'])
        self.epsilon_decay = float(config[self.env]['epsilon_decay'])
        self.critic_net_learnrate_init = float(config[self.env]['critic_net_learnrate_init'])
        self.critic_net_learnrate_decay = float(config[self.env]['critic_net_learnrate_decay'])
        self.critic_net_clipnorm = float(config[self.env]['critic_net_clipnorm'])
        self.target_update_freq = float(config[self.env]['target_update_freq'])
        self.timeslip_size = int(config[self.env]['timeslip_size'])
        self.timeslip = np.zeros(shape=(self.greedysnake.SIZE, self.greedysnake.SIZE, self.timeslip_size))

        # parameters
        self.total_steps = 0
        self.critic_net_learnrate = self.critic_net_learnrate_init * (self.critic_net_learnrate_decay ** self.total_steps)
        self.epsilon = self.epsilon_init * (self.epsilon_decay ** self.total_steps)

    def write_to_timeslip(self):
        display = ''
        frame = np.zeros(shape=(self.greedysnake.SIZE, self.greedysnake.SIZE), dtype=np.float32)
        # generate states for N(s, a)
        for i in range(self.greedysnake.SIZE ** 2):
            row = i // self.greedysnake.SIZE
            col = i % self.greedysnake.SIZE
            snake_index = self.greedysnake.is_snake(row, col)

            # snake
            if snake_index > -1:

                # snake head
                if snake_index == 0: 
                    frame[row, col] = 0.5
                    display += '@'

                # snake body
                else:
                    frame[row, col] = 0.3
                    display += 'O'

            # food
            elif (np.array([row, col]) == self.greedysnake.food).all():
                frame[row, col] = 1.0
                display += '#'
            
            # block
            else: 
                frame[row, col] = 0.
                display += '-'

            # switch line
            if col == self.greedysnake.SIZE - 1:
                display += '\n'
            # store frame to timeslip

        self.timeslip = np.insert(self.timeslip, 0, frame, axis=2)
        self.timeslip = np.delete(self.timeslip, self.timeslip_size, axis=2)
        return display
    
    def get_action(self, state, critic_model, epsilon):
        rand_strategy = np.random.rand()
        # random action
        if 0 <= rand_strategy <= epsilon:
            q = critic_model.predict(np.array(state).reshape((1, self.greedysnake.SIZE, self.greedysnake.SIZE, self.timeslip_size)))
            sm = np.array(tf.nn.softmax(q)).reshape((4))
            rand = np.random.randint(0, 4)
            action = None
            if rand == 0:
                action = Direction.UP
            elif rand == 1:
                action = Direction.DOWN
            elif rand == 2:
                action = Direction.LEFT
            elif rand == 3:
                action = Direction.RIGHT
            return action, q, sm
        # greedy
        else:
            q = critic_model.predict(np.array(state).reshape((1, self.greedysnake.SIZE, self.greedysnake.SIZE, self.timeslip_size)))
            sm = np.array(tf.nn.softmax(q)).reshape((4))
            q_np = np.array(q).reshape((4))
            argmax = np.argmax(q_np)
            action = None
            if argmax == 0:
                action = Direction.UP
            elif argmax == 1:
                action = Direction.DOWN
            elif argmax == 2:
                action = Direction.LEFT
            elif argmax == 3:
                action = Direction.RIGHT
            return action, q, sm

    def get_action_index(self, action):
        if action == Direction.UP:
            return 0
        elif action == Direction.DOWN:
            return 1
        elif action == Direction.LEFT:
            return 2
        elif action == Direction.RIGHT:
            return 3
        
    def get_ddqn(self):

        initializer = keras.initializers.RandomNormal()

        # critic layers
        critic_model = keras.Sequential([
            keras.layers.Input(shape = (self.greedysnake.SIZE, self.greedysnake.SIZE, self.timeslip_size)),
            keras.layers.Conv2D(
                24, (5, 5), 
                padding='same', 
                activation='relu', 
                kernel_initializer=initializer, 
            ),
            keras.layers.Conv2D(
                24, (3, 3), 
                padding='same', 
                activation='relu', 
                kernel_initializer=initializer, 
            ),
            keras.layers.Conv2D(
                24, (3, 3), 
                padding='same', 
                activation='relu', 
                kernel_initializer=initializer, 
            ),
            keras.layers.Conv2D(
                24, (3, 3), 
                padding='same', 
                activation='relu', 
                kernel_initializer=initializer, 
            ),
            keras.layers.Conv2D(
                24, (3, 3), 
                padding='same', 
                activation='relu', 
                kernel_initializer=initializer, 
            ),
            keras.layers.Flatten(),
            keras.layers.Dense(1280, activation = 'relu', kernel_initializer=initializer),
            keras.layers.Dense(256, activation = 'relu', kernel_initializer=initializer),
            keras.layers.Dense(4, kernel_initializer=initializer)
        ], name = 'critic')

        # optimizer
        c_opt = keras.optimizers.Adam(
            lr = self.critic_net_learnrate, 
            clipnorm = self.critic_net_clipnorm
        )
        
        # critic model
        critic_model.compile(loss = keras.losses.MSE, optimizer = c_opt)

        # target model
        target = keras.models.clone_model(critic_model)
        target.set_weights(critic_model.get_weights())
        return critic_model, target
        
    def run(self):
        # record random initial steps
        for i in range(self.timeslip_size + 1):
            rand = np.random.randint(0, 4)
            a = None
            if rand == 0:
                a = Direction.UP
            elif rand == 1:
                a = Direction.DOWN
            elif rand == 2:
                a = Direction.LEFT
            elif rand == 3:
                a = Direction.RIGHT
            self.greedysnake.step(a)
            display = self.write_to_timeslip()
            print('=========Initial Steps===========')
            print(display)
        
        # define deep learning network
        critic_model, target = self.get_ddqn()
        
        # statics
        scores = deque(maxlen=1000)
        max_score = 0
        hits = 0
        eats = 0

        for e in range(self.max_epochs):

            # execute steps for greedy snake
            s_arr = deque()
            s_a_future_arr = deque()
            r_arr = deque()
            t_arr = deque()
            q_arr = deque()

            # buffer
            s_current_temp = None
            a_current_temp = None
            
            # start steps
            stamina = 0
            stamina_max = self.greedysnake.SIZE
            for i in range(self.max_steps):

                # observe state and action at t = 0
                if i == 0:
                    s_current = self.timeslip
                    a_current = self.get_action(s_current, critic_model, self.epsilon)[0]
                else: 
                    s_current = s_current_temp
                    a_current = a_current_temp
                s_arr.append(s_current)

                # take action via eps greedy, get reward
                signal = self.greedysnake.step(a_current)
                r = None

                # signal reward
                if signal == Signal.HIT:
                    r = -1
                    stamina = 0
                    hits += 1
                elif signal == Signal.EAT:
                    r = 1
                    stamina = stamina_max
                    eats += 1
                elif signal == Signal.NORMAL:
                    stamina -= 1
                    if stamina < 0:
                        stamina = 0
                    r = stamina / stamina_max

                r_arr.append(r)

                # observe state after action
                display = self.write_to_timeslip()
                s_future = self.timeslip
                s_current_temp = s_future
                s_a_future_arr.append(s_future)
                
                # choose action at t+1
                get_action_result = self.get_action(s_future, critic_model, self.epsilon)
                a_future = get_action_result[0]
                a_current_temp = a_future

                # get teacher for critic net (online learning)
                q_current = critic_model.predict(s_current.reshape((1, self.greedysnake.SIZE, self.greedysnake.SIZE, self.timeslip_size)))
                target_sa = target.predict(s_future.reshape(1, self.greedysnake.SIZE, self.greedysnake.SIZE, self.timeslip_size))
                t = [0,0,0,0]
                index = np.argmax(np.array(target_sa).reshape((4)))
                for j in range(len(t)):
                    if j == self.get_action_index(a_current):
                        t[j] = r + self.gamma * np.array(target_sa).reshape((4))[index]
                        if signal == Signal.HIT and j == self.get_action_index(a_current):
                            t[j] = r
                    else:
                        t[j] = np.array(q_current).reshape((4))[j]
                q_arr.append(q_current)
                t_arr.append(t)

                # accumulate index
                self.total_steps += 1

                # update learn rate and eps
                self.critic_net_learnrate = self.critic_net_learnrate_init * (self.critic_net_learnrate_decay ** self.total_steps)
                self.epsilon = self.epsilon_init * (self.epsilon_decay ** self.total_steps)
                K.set_value(critic_model.optimizer.learning_rate, self.critic_net_learnrate)

                # display information
                a_print = str(a_future)
                r_print = str(float(r))
                t_print = str(np.array(t))
                predict_print = str(q_current)
                diff_print = str(abs(t - q_current))

                # calc stats
                scores.append(len(self.greedysnake.snake))
                avg = sum(scores) / len(scores)
                if avg > max_score:
                    max_score = avg

                # print to debug
                print('Step = ' + str(i) + ' / Epoch = ' + str(e) + ' / Total Steps = ' + str(self.total_steps))
                print('action = ' + a_print + ' / reward = ' + r_print)
                print('teacher(Q) = ' + t_print + ' / predict(Q) = ' + predict_print +' / diff = ' + diff_print)
                print('thousand steps average score = ' + str(avg))
                print('max avg. score = ' + str(max_score))
                print('Hit rate = ' + str(hits / self.total_steps))
                print('Eat rate = ' + str(eats / self.total_steps))
                print(display)

                
                if self.total_steps % self.target_update_freq == 0 and self.total_steps != 0:
                    print('clone critic weights to target')
                    target.set_weights(critic_model.get_weights())

                if self.total_steps % 1000 == 0:
                    print('models saved')
                    critic_model.save('ddqn_critic')
                    target.save('ddqn_target')

            # train steps
            s = np.array(s_arr, dtype=np.float32).reshape((len(s_arr), self.greedysnake.SIZE, self.greedysnake.SIZE, self.timeslip_size))
            t = np.array(t_arr, dtype=np.float32).reshape((len(t_arr), 4))
            r = np.array(r_arr, dtype=np.float32).reshape((len(r_arr), 1))
            critic_model.fit(s, t, epochs=self.critic_net_epochs, verbose=0, batch_size = self.batch_size)

            # record train history
            #f.write(str(critic_hist.history)+'\n')
            #f.write(str(actor_hist.history)+'\n')
            #f.close()


if __name__ == "__main__":
    d = Driver()
    d.run()
        
