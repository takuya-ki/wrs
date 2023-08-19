import visualization.panda.world as wd
import modeling.geometric_model as gm
import modeling.collision_model as cm
import basis.robot_math as rm
import numpy as np
import itertools
import robot_sim.robots.cobotta.cobotta as cbt


# base = wd.World(cam_pos=[3, 1, 2], lookat_pos=[0, 0, 0])
# gm.gen_frame().attach_to(base)
# rbt_s = cbt.Cobotta()
# rbt_s.gen_meshmodel().attach_to(base)
#
# jnt_rngs = rbt_s.get_jnt_ranges(component_name='arm')
# jnb = [90, 90, 60, 30, 30, 10]
# j1_bins = np.linspace(jnt_rngs[0][0], jnt_rngs[0][1], jnb[0])
# j2_bins = np.linspace(jnt_rngs[0][0], jnt_rngs[0][1], jnb[1])
# j3_bins = np.linspace(jnt_rngs[0][0], jnt_rngs[0][1], jnb[2])
# j4_bins = np.linspace(jnt_rngs[0][0], jnt_rngs[0][1], jnb[3])
# j5_bins = np.linspace(jnt_rngs[0][0], jnt_rngs[0][1], jnb[4])
# j6_bins = np.linspace(jnt_rngs[0][0], jnt_rngs[0][1], jnb[5])
#
# n_total = np.prod(jnb)
# result = itertools.product(j1_bins, j2_bins, j3_bins, j4_bins, j5_bins, j6_bins)
# cnter = 0
# for c in result:
#     cnter = cnter + 1
#     print(cnter, "/", n_total, ",", cnter / n_total)
#     rbt_s.fk(jnt_values=np.asarray(c))
#     tcp_gl_pos, tcp_gl_rotmat = rbt_s.get_gl_tcp()
#     print(tcp_gl_pos, rm.quaternion_from_matrix(tcp_gl_rotmat))
#
# base.run()

def gen_data(rbt_s,
             component_name='arm',
             granularity=[np.radians(4), np.radians(4), np.radians(6), np.radians(12), np.radians(12), np.radians(30)],
             save_name='cobotta_ik.csv'):
    n_jnts = rbt_s.manipulator_dict[component_name].ndof
    all_ranges = []
    for jnt_id in range(1, n_jnts + 1):
        r0, r1 = rbt_s.manipulator_dict[component_name].jnts[jnt_id]['motion_rng']
        all_ranges.append(np.arange(r0, r1, granularity[jnt_id - 1]))
        # print(granularity, all_ranges[-1])
    all_data = itertools.product(*all_ranges)
    n_data = 1
    for rngs in all_ranges:
        n_data = n_data * len(rngs)
    data_set_tcp = []
    data_set_jnts = []
    in_data_npy = np.empty((0, 6))
    for i, data in enumerate(all_data):
        print(i, n_data, i/n_data)
        rbt_s.fk(component_name=component_name, jnt_values=np.array(data))
        xyz, rotmat = rbt_s.get_gl_tcp(manipulator_name=component_name)
        # qt = rm.quaternion_from_matrix(rotmat)
        in_data = np.asarray(xyz.tolist()+rm.rotmat_to_euler(rotmat).tolist())
        # diff = np.sum(np.abs(np.array(in_data) - in_data_npy), 1)
        # if np.any(diff < 1e-4):
        #     print(diff)
        #     input("Press Enter to continue...")
        in_data_npy = np.vstack((in_data_npy, in_data))
        out_data = data
        data_set_tcp.append(in_data)
        data_set_jnts.append(out_data)
    # df = pd.DataFrame(data_set, columns=['xyzrpy', 'jnt_values'])
    # df.to_csv(save_name)
    # np.save(save_name + "_min_max", np.array([np.min(in_data_npy, 0), np.max(in_data_npy, 0)]))
    np.save(save_name+"_tcp", np.array(data_set_tcp))
    np.save(save_name+"_jnts", np.array(data_set_jnts))


if __name__ == '__main__':
    rbt_s = cbt.Cobotta()
    # granularity1 = [np.radians(12), np.radians(12), np.radians(18), np.radians(24), np.radians(24), np.radians(36)]
    granularity1 = [np.radians(20), np.radians(20), np.radians(30), np.radians(45), np.radians(45), np.radians(60)]
    gen_data(rbt_s, granularity=granularity1, save_name='cobotta_ik')
    # granularity2 = [np.radians(13), np.radians(13), np.radians(19), np.radians(25), np.radians(25), np.radians(37)]
    # granularity2 = [np.radians(21), np.radians(21), np.radians(31), np.radians(46), np.radians(46), np.radians(61)]
    # gen_data(rbt_s, granularity=granularity2, save_name='cobotta_ik_test')
