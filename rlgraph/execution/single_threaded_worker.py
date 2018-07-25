# Copyright 2018 The YARL-Project, All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
from six.moves import xrange as range_
import time

from yarl import YARLError
from yarl.utils.util import default_dict
from yarl.execution.worker import Worker


class SingleThreadedWorker(Worker):

    def __init__(self, **kwargs):
        """
        Keyword Args:
            render (bool): Whether to render the environment after each action. Default: False.
        """
        self.render = kwargs.pop("render", False)

        super(SingleThreadedWorker, self).__init__(**kwargs)

        self.logger.info("Initialized single-threaded executor with Environment '{}' and Agent '{}'".format(
            self.environment, self.agent
        ))

        self.env_frames = 0
        self.episode_rewards = list()
        self.episode_durations = list()
        self.episode_steps = list()
        # Accumulated return over the running episode.
        self.episode_return = 0
        # The number of steps taken in the running episode.
        self.episode_timesteps = 0
        # Whether the running episode has terminated.
        self.episode_terminal = False
        # Wall time of the last start of the running episode.
        self.episode_start = None
        # The current state of the running episode.
        self.episode_state = None

    def execute_timesteps(self, num_timesteps, max_timesteps_per_episode=0, update_spec=None, use_exploration=True,
                          frameskip=None, reset=True):
        return self._execute(
            num_timesteps=num_timesteps,
            max_timesteps_per_episode=max_timesteps_per_episode,
            use_exploration=use_exploration,
            update_spec=update_spec,
            frameskip=frameskip,
            reset=reset
        )

    def execute_episodes(self, num_episodes, max_timesteps_per_episode=0, update_spec=None, use_exploration=True,
                         frameskip=None, reset=True):
        return self._execute(
            num_episodes=num_episodes,
            max_timesteps_per_episode = max_timesteps_per_episode,
            use_exploration=use_exploration,
            update_spec=update_spec,
            frameskip=frameskip,
            reset=reset
        )

    def _execute(
        self,
        num_timesteps=None,
        num_episodes=None,
        max_timesteps_per_episode=None,
        use_exploration=True,
        update_spec=None,
        frameskip=None,
        reset=True
    ):
        """
        Actual implementation underlying `execute_timesteps` and `execute_episodes`.

        Args:
            num_timesteps (Optional[int]): The maximum number of timesteps to run. At least one of `num_timesteps` or
                `num_episodes` must be provided.
            num_episodes (Optional[int]): The maximum number of episodes to run. At least one of `num_timesteps` or
                `num_episodes` must be provided.
            use_exploration (Optional[bool]): Indicates whether to utilize exploration (epsilon or noise based)
                when picking actions. Default: True.
            max_timesteps_per_episode (Optional[int]): Can be used to limit the number of timesteps per episode.
                Use None or 0 for no limit. Default: None.
            update_spec (Optional[dict]): Update parameters. If None, the worker only performs rollouts.
                Matches the structure of an Agent's update_spec dict and will be "defaulted" by that dict.
                See `input_parsing/parse_update_spec.py` for more details.
            frameskip (Optional[int]): How often actions are repeated after retrieving them from the agent.
                Rewards are accumulated over the number of skips. Use None for the Worker's default value.
            reset (bool): Whether to reset the environment and all the Worker's internal counters.
                Default: True.

        Returns:
            dict: Execution statistics.
        """
        assert num_timesteps is not None or num_episodes is not None,\
            "ERROR: One of `num_timesteps` or `num_episodes` must be provided!"
        # Are we updating or just acting/observing?
        update_spec = default_dict(update_spec, self.agent.update_spec)
        self.set_update_schedule(update_spec)

        num_timesteps = num_timesteps or 0
        num_episodes = num_episodes or 0
        max_timesteps_per_episode = max_timesteps_per_episode or 0
        frameskip = frameskip or self.frameskip

        # Stats.
        timesteps_executed = 0
        episodes_executed = 0

        if reset is True:
            self.env_frames = 0
            self.episode_rewards = list()
            self.episode_durations = list()
            self.episode_steps = list()

        start = time.monotonic()

        # Only run everything for at most num_timesteps (if defined).
        while not (0 < num_timesteps <= timesteps_executed):
            # If we are in a second or later loop OR reset is True -> Reset the Env and the Agent.
            if timesteps_executed != 0 or reset is True or self.episode_terminal is True:
                self.episode_return = 0
                self.episode_timesteps = 0
                self.episode_terminal = False
                self.episode_start = time.monotonic()
                self.episode_state = self.environment.reset()
                self.agent.reset()
            elif self.episode_state is None:
                raise YARLError("Runner must be reset at the very beginning. Environment is in invalid state.")

            if self.render:
                self.environment.render()

            while True:
                action, preprocessed_state = self.agent.get_action(
                    states=self.episode_state, use_exploration=use_exploration, extra_returns="preprocessed_states"
                )

                # Accumulate the reward over n env-steps (equals one action pick). n=self.frameskip.
                reward = 0
                next_state = None
                for _ in range_(frameskip):
                    next_state, step_reward, self.episode_terminal, info = self.environment.step(actions=action)
                    self.env_frames += 1
                    reward += step_reward
                    if self.episode_terminal:
                        break

                # Only render once per action.
                if self.render:
                    self.environment.render()

                self.episode_return += reward
                timesteps_executed += 1
                self.episode_timesteps += 1

                num_timesteps_reached = (0 < num_timesteps <= timesteps_executed)
                max_episode_timesteps_reached = (0 < max_timesteps_per_episode <= self.episode_timesteps)
                # The episode was aborted artificially (without actually being terminal).
                # Change the last terminal flag to True.
                if max_episode_timesteps_reached:
                    self.episode_terminal = True

                self.agent.observe(
                    preprocessed_states=preprocessed_state, actions=action, internals=[], rewards=reward,
                    terminals=self.episode_terminal
                )

                self.episode_state = next_state

                self.update_if_necessary()

                # Is the episode finished or do we have to terminate it prematurely because of other restrictions?
                if self.episode_terminal or num_timesteps_reached or max_episode_timesteps_reached:
                    break

            episodes_executed += 1
            self.episode_rewards.append(self.episode_return)
            self.episode_durations.append(time.monotonic() - self.episode_start)
            self.episode_steps.append(self.episode_timesteps)
            self.logger.info("Finished episode: reward={}, actions={}, duration={}s.".format(
                self.episode_return, self.episode_timesteps, self.episode_durations[-1]))

            if 0 < num_episodes <= episodes_executed:
                break

        total_time = (time.monotonic() - start) or 1e-10

        results = dict(
            runtime=total_time,
            # Agent act/observe throughput.
            timesteps_executed=timesteps_executed,
            ops_per_second=(timesteps_executed / total_time),
            # Env frames including action repeats.
            env_frames=self.env_frames,
            env_frames_per_second=(self.env_frames / total_time),
            episodes_executed=episodes_executed,
            episodes_per_minute=(episodes_executed/(total_time / 60)),
            mean_episode_runtime=np.mean(self.episode_durations),
            mean_episode_reward=np.mean(self.episode_rewards),
            max_episode_reward=np.max(self.episode_rewards),
            final_episode_reward=self.episode_rewards[-1]
        )

        # Total time of run.
        self.logger.info("Finished execution in {} s".format(total_time))
        # Total (RL) timesteps (actions) done (and timesteps/sec).
        self.logger.info("Time steps (actions) executed: {} ({} ops/s)".
                         format(results['timesteps_executed'], results['ops_per_second']))
        # Total env-timesteps done (including action repeats) (and env-timesteps/sec).
        self.logger.info("Env frames executed (incl. action repeats): {} ({} frames/s)".
                         format(results['env_frames'], results['env_frames_per_second']))
        # Total episodes done (and episodes/min).
        self.logger.info("Episodes finished: {} ({} episodes/min)".
                         format(results['episodes_executed'], results['episodes_per_minute']))
        self.logger.info("Mean episode runtime: {}s".format(results['mean_episode_runtime']))
        self.logger.info("Mean episode reward: {}".format(results['mean_episode_reward']))
        self.logger.info("Max. episode reward: {}".format(results['max_episode_reward']))
        self.logger.info("Final episode reward: {}".format(results['final_episode_reward']))

        return results