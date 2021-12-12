import math
import time
import itertools
import numpy as np
import pandas as pd
import basis.robot_math as rm
import modeling.geometric_model as gm
import visualization.panda.world as world
import robot_sim.robots.cobotta.cobotta as cbt_s


def gen_training_data(rbt_s, component_name = 'arm', granularity=math.pi/4):
    n_jnts = rbt_s.manipulator_dict[component_name].ndof
    all_ranges = []
    for jnt_id in range(1, n_jnts+1):
        r0, r1 = rbt_s.manipulator_dict[component_name].jnts[jnt_id]['motion_rng']
        all_ranges.append(np.arange(r0, r1, granularity))
        # print(granularity, all_ranges[-1])
    all_data = itertools.product(*all_ranges)
    n_data = 1
    for rngs in all_ranges:
        n_data = n_data*len(rngs)
    data_set = []
    for i, data in enumerate(all_data):
        print(i, n_data)
        rbt_s.fk(component_name=component_name, jnt_values=np.array(data))
        xyz, rotmat = rbt_s.get_gl_tcp(manipulator_name=component_name)
        rm.rotmat
        rpy = rm.rotmat_to_euler(rotmat)
        input = (xyz[0], xyz[1], xyz[2], rpy[0], rpy[1], rpy[2])
        output = data
        data_set.append([input, output])
    df = pd.DataFrame(data_set, columns=['xyzquat', 'jnt_values'])
    df.to_csv('cobotta_ik_test.csv')


if __name__ == '__main__':
    base = world.World(cam_pos=np.array([1.5, 1, .7]))
    gm.gen_frame().attach_to(base)
    rbt_s = cbt_s.Cobotta()
    rbt_s.gen_meshmodel(toggle_tcpcs=True).attach_to(base)
    gen_training_data(rbt_s)
    base.run()
