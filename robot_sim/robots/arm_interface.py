import copy
import numpy as np
import robot_sim._kinematics.collision_checker as cc


class ArmInterface(object):
    """
    An arm is a combination of a manipulator and an end-effector
    author: weiwei
    date: 20230607
    """

    def __init__(self, pos=np.zeros(3), rotmat=np.eye(3), name='arm_interface'):
        # TODO self.jlcs = {}
        self.name = name
        self.pos = pos
        self.rotmat = rotmat
        # collision detection
        self.cc = None
        # component map for quick access
        self.manipulator = None
        self.end_effector = None
        # a list of detailed information about objects in hand, see CollisionChecker.add_objinhnd
        self.oih_infos = []  # object in hand

    def _update_oih(self):
        """
        oih = object in hand
        :return:
        author: weiwei
        date: 20230807
        """
        for obj_info in self.oih_infos:
            gl_pos, gl_rotmat = self.cvt_loc_tcp_to_gl(obj_info['rel_pos'], obj_info['rel_rotmat'])
            obj_info['gl_pos'] = gl_pos
            obj_info['gl_rotmat'] = gl_rotmat

    def _update_oof(self):
        """
        oof = object on flange
        this function is to be implemented by subclasses for updating ft-sensors, tool changers, end-effectors, etc.
        :return:
        author: weiwei
        date: 20230807
        """
        raise NotImplementedError

    def change_name(self, name):
        self.name = name

    def get_jnt_ranges(self):
        return self.manipulator.get_jnt_ranges()

    def get_jnt_values(self):
        return self.manipulator.get_jnt_values()

    def get_gl_tcp(self):
        return self.manipulator.get_gl_tcp()

    def is_jnt_values_in_ranges(self, jnt_values):
        return self.manipulator.is_jnt_values_in_ranges(jnt_values)

    def fix_to(self, pos, rotmat):
        self.pos = pos
        self.rotmat = rotmat
        self.manipulator.fix_to(pos=pos, rotmat=rotmat)
        self._update_oof()
        self._update_oih()

    def fk(self, jnt_values=np.zeros(6)):
        """
        :param jnt_values: 7 or 3+7, 3=agv, 7=arm, 1=grpr; metrics: meter-radian
        :param component_name: 'arm', 'agv', or 'all'
        :return:
        author: weiwei
        date: 20201208, 20230807toyonaka
        """
        if not isinstance(jnt_values, np.ndarray) or jnt_values.size != 6:
            raise ValueError("An 1x6 npdarray must be specified to move the arm!")
        self.manipulator.fk(jnt_values)
        self._update_oof()

    def ik(self,
           tgt_pos=np.zeros(3),
           tgt_rotmat=np.eye(3),
           seed_jnt_values=None,
           max_niter=200,
           tcp_jnt_id=None,
           tcp_loc_pos=None,
           tcp_loc_rotmat=None,
           local_minima: str = "end",
           toggle_debug=False):
        return self.manipulator.ik(tgt_pos,
                                   tgt_rotmat,
                                   seed_jnt_values=seed_jnt_values,
                                   max_niter=max_niter,
                                   tcp_jnt_id=tcp_jnt_id,
                                   tcp_loc_pos=tcp_loc_pos,
                                   tcp_loc_rotmat=tcp_loc_rotmat,
                                   local_minima=local_minima,
                                   toggle_debug=toggle_debug)

    def manipulability(self,
                       tcp_jnt_id=None,
                       tcp_loc_pos=None,
                       tcp_loc_rotmat=None):
        return self.manipulator.manipulability(tcp_jnt_id=tcp_jnt_id,
                                               tcp_loc_pos=tcp_loc_pos,
                                               tcp_loc_rotmat=tcp_loc_rotmat)

    def manipulability_axmat(self,
                             tcp_jnt_id=None,
                             tcp_loc_pos=None,
                             tcp_loc_rotmat=None,
                             type="translational"):
        return self.mmanipulator.manipulability_axmat(tcp_jnt_id=tcp_jnt_id,
                                                      tcp_loc_pos=tcp_loc_pos,
                                                      tcp_loc_rotmat=tcp_loc_rotmat,
                                                      type=type)

    def jacobian(self,
                 tcp_jnt_id=None,
                 tcp_loc_pos=None,
                 tcp_loc_rotmat=None):
        return self.mmanipulator.jacobian(tcp_jnt_id=tcp_jnt_id,
                                          tcp_loc_pos=tcp_loc_pos,
                                          tcp_loc_rotmat=tcp_loc_rotmat)

    def rand_conf(self):
        return self.manipulator.rand_conf()

    def cvt_conf_to_tcp(self, jnt_values):
        """
        given jnt_values, this function returns the correspondent global tcp_pos, and tcp_rotmat
        :param jnt_values:
        :return:
        author: weiwei
        date: 20210417
        """
        jnt_values_bk = self.get_jnt_values()
        self.fk(jnt_values)
        gl_tcp_pos, gl_tcp_rotmat = self.manipulator.get_gl_tcp()
        self.fk(jnt_values_bk)
        return gl_tcp_pos, gl_tcp_rotmat

    def cvt_gl_to_loc_tcp(self, gl_obj_pos, gl_obj_rotmat):
        return self.manipulator.cvt_gl_to_loc_tcp(gl_obj_pos, gl_obj_rotmat)

    def cvt_loc_tcp_to_gl(self, rel_obj_pos, rel_obj_rotmat):
        return self.manipulator.cvt_loc_tcp_to_gl(rel_obj_pos, rel_obj_rotmat)

    def get_oih_list(self):
        return_list = []
        for obj_info in self.oih_infos:
            objcm = obj_info['collision_model']
            objcm.set_pos(obj_info['gl_pos'])
            objcm.set_rotmat(obj_info['gl_rotmat'])
            return_list.append(objcm)
        return return_list

    def release(self, objcm, jawwidth=None):
        """
        the objcm is added as a part of the robot_s to the cd checker
        :param jawwidth:
        :param objcm:
        :return:
        """
        if jawwidth is not None:
            self.end_effector.jaw_to(jawwidth)
        for obj_info in self.oih_infos:
            if obj_info['collision_model'] is objcm:
                self.cc.delete_cdobj(obj_info)
                self.oih_infos.remove(obj_info)
                break

    def is_collided(self, obstacle_list=None, otherrobot_list=None, toggle_contact_points=False):
        """
        Interface for "is cdprimit collided", must be implemented in child class
        :param obstacle_list:
        :param otherrobot_list:
        :param toggle_contact_points: debug
        :return: see CollisionChecker is_collided for details
        author: weiwei
        date: 20201223
        """
        if obstacle_list is None:
            obstacle_list = []
        if otherrobot_list is None:
            otherrobot_list = []
        collision_info = self.cc.is_collided(obstacle_list=obstacle_list,
                                             otherrobot_list=otherrobot_list,
                                             toggle_contact_points=toggle_contact_points)
        return collision_info

    def show_cdprimit(self):
        self.cc.show_cdprimit()

    def unshow_cdprimit(self):
        self.cc.unshow_cdprimit()

    def gen_stickmodel(self,
                       tcp_jnt_id=None,
                       tcp_loc_pos=None,
                       tcp_loc_rotmat=None,
                       toggle_tcpcs=False,
                       toggle_jntscs=False,
                       toggle_connjnt=False,
                       name='arm_interface_stickmodel'):
        raise NotImplementedError

    def gen_meshmodel(self,
                      tcp_jnt_id=None,
                      tcp_loc_pos=None,
                      tcp_loc_rotmat=None,
                      toggle_tcpcs=False,
                      toggle_jntscs=False,
                      rgba=None,
                      name='arm_interface_meshmodel'):
        raise NotImplementedError

    def enable_cc(self):
        self.cc = cc.CollisionChecker("collision_checker")

    def disable_cc(self):
        """
        clear pairs and nodepath
        :return:
        """
        for cdelement in self.cc.all_cdelements:
            cdelement['cdprimit_childid'] = -1
        self.cc = None

    def copy(self):
        self_copy = copy.deepcopy(self)
        # deepcopying colliders are problematic, I have to update it manually
        if self_copy.cc is not None:
            for child in self_copy.cc.np.getChildren():
                self_copy.cc.ctrav.addCollider(child, self_copy.cc.chan)
        return self_copy
