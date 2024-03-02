import os
import math
import numpy as np
import basis.robot_math as rm
import modeling.model_collection as mc
import modeling.collision_model as cm
import robot_sim._kinematics.jlchain as jl
import robot_sim.system.system_interface as ri
import robot_sim.robots.khi.khi_or2fg7 as kg
import robot_sim.robots.khi.khi_orsd as ksd


class KHI_DUAL(ri.RobotInterface):
    """
    author: weiwei
    date: 20230805 Toyonaka
    """

    def __init__(self, pos=np.zeros(3), rotmat=np.eye(3), name='khi_dual', enable_cc=True):
        super().__init__(pos=pos, rotmat=rotmat, name=name)
        this_dir, this_filename = os.path.split(__file__)
        lft_arm_homeconf = np.radians(np.array([0, 0, 0, 0, 0, 0]))
        rgt_arm_homeconf = np.radians(np.array([0, 0, 0, 0, 0, 0]))
        # base
        self.base_table = jl.JLChain(pos=pos, rotmat=rotmat, home_conf=np.zeros(0), name='base_table')
        self.base_table.lnks[0]['name'] = "base_table"
        self.base_table.jnts[-1]['loc_pos'] = np.array([0, -.4, .726])
        self.base_table.lnks[0]['collision_model'] = cm.CollisionModel(
            os.path.join(this_dir, "meshes", "base_table.stl"))
        # pre-comptue coordinates
        lr_rotmat = rm.rotmat_from_euler(0, 0, np.radians(-90))
        lft_pos = self.base_table.jnts[-1]['loc_pos']
        rgt_pos = lft_pos + np.array([0, .8, 0])
        # lft
        self.lft_arm = kg.KHI_OR2FG7(pos=lft_pos, rotmat=lr_rotmat, enable_cc=False)
        self.lft_arm.fk(jnt_values=lft_arm_homeconf)
        # rgt
        self.rgt_arm = ksd.KHI_ORSD(pos=rgt_pos, rotmat=lr_rotmat, enable_cc=False)
        self.rgt_arm.fk(jnt_values=rgt_arm_homeconf)
        # collision detection
        if enable_cc:
            self.enable_cc()
        # component map
        self.manipulator_dict['rgt_arm'] = self.lft_arm
        self.manipulator_dict['lft_arm'] = self.rgt_arm

    def enable_cc(self):
        # TODO when pose is changed, oih info goes wrong
        pass
        # super().enable_cc()
        # self.cc.add_cdlnks(self.central_body, [0, 1, 2, 3])
        # self.cc.add_cdlnks(self.lft_arm, [2, 3, 4, 5, 6, 7])
        # self.cc.add_cdlnks(self.rgt_arm, [2, 3, 4, 5, 6, 7])
        # activelist = [self.lft_arm.lnks[2],
        #               self.lft_arm.lnks[3],
        #               self.lft_arm.lnks[4],
        #               self.lft_arm.lnks[5],
        #               self.lft_arm.lnks[6],
        #               self.lft_arm.lnks[7],
        #               self.rgt_arm.lnks[2],
        #               self.rgt_arm.lnks[3],
        #               self.rgt_arm.lnks[4],
        #               self.rgt_arm.lnks[5],
        #               self.rgt_arm.lnks[6],
        #               self.rgt_arm.lnks[7]]
        # self.cc.set_active_cdlnks(activelist)
        # fromlist = [self.central_body.lnks[0],
        #             self.central_body.lnks[1],
        #             self.central_body.lnks[3],
        #             self.lft_arm.lnks[2],
        #             self.rgt_arm.lnks[2]]
        # intolist = [self.lft_arm.lnks[5],
        #             self.lft_arm.lnks[6],
        #             self.lft_arm.lnks[7],
        #             self.rgt_arm.lnks[5],
        #             self.rgt_arm.lnks[6],
        #             self.rgt_arm.lnks[7]]
        # self.cc.set_cdpair(fromlist, intolist)
        # fromlist = [self.lft_arm.lnks[5],
        #             self.lft_arm.lnks[6],
        #             self.lft_arm.lnks[7]]
        # intolist = [self.rgt_arm.lnks[5],
        #             self.rgt_arm.lnks[6],
        #             self.rgt_arm.lnks[7]]
        # self.cc.set_cdpair(fromlist, intolist)

    def get_hnd_on_manipulator(self, manipulator_name):
        pass
        # if hnd_name == 'rgt_arm':
        #     return self.rgt_hnd
        # elif hnd_name == 'lft_arm':
        #     return self.lft_hnd
        # else:
        #     raise ValueError("The given jlc does not have a hand!")

    def fix_to(self, pos, rotmat):
        super().fix_to(pos, rotmat)
        self.pos = pos
        self.rotmat = rotmat
        self.base_table.fix_to(self.pos, self.rotmat)
        self.lft_arm.fix_to(self.pos, self.rotmat)
        # self.lft_hnd.fix_to(pos=self.lft_arm.joints[-1]['gl_posq'],
        #                     rotmat=self.lft_arm.joints[-1]['gl_rotmatq'])
        self.rgt_arm.fix_to(self.pos, self.rotmat)
        # self.rgt_hnd.fix_to(pos=self.rgt_arm.joints[-1]['gl_posq'],
        #                     rotmat=self.rgt_arm.joints[-1]['gl_rotmatq'])

    def fk(self, component_name, jnt_values):
        """
        waist angle is transmitted to arms
        :param jnt_values: nparray 1x6 or 1x14 depending on component_names
        :hnd_name 'lft_arm', 'rgt_arm', 'lft_arm_waist', 'rgt_arm_wasit', 'both_arm'
        :param component_name:
        :return:
        author: weiwei
        date: 20201208toyonaka
        """

        def update_oih(component_name='rgt_arm_waist'):
            # inline function for update objects in hand
            if component_name[:7] == 'rgt_arm':
                oih_info_list = self.rgt_oih_infos
            elif component_name[:7] == 'lft_arm':
                oih_info_list = self.lft_oih_infos
            for obj_info in oih_info_list:
                gl_pos, gl_rotmat = self.cvt_loc_tcp_to_gl(component_name, obj_info['rel_pos'], obj_info['rel_rotmat'])
                obj_info['gl_pos'] = gl_pos
                obj_info['gl_rotmat'] = gl_rotmat

        def update_component(component_name, jnt_values):
            status = self.manipulator_dict[component_name].fk(joint_values=jnt_values)
            hnd_on_manipulator = self.get_hnd_on_manipulator(component_name)
            if hnd_on_manipulator is not None:
                hnd_on_manipulator.fix_to(pos=self.manipulator_dict[component_name].jnts[-1]['gl_posq'],
                                          rotmat=self.manipulator_dict[component_name].jnts[-1]['gl_rotmatq'])
            update_oih(component_name=component_name)
            return status

        # examine axis_length
        if component_name == 'lft_arm' or component_name == 'rgt_arm':
            if not isinstance(jnt_values, np.ndarray) or jnt_values.size != 6:
                raise ValueError("An 1x6 npdarray must be specified to move a single arm!")
            waist_value = self.base_table.jnts[1]['motion_value']
            return update_component(component_name, np.append(waist_value, jnt_values))
        elif component_name == 'lft_arm_waist' or component_name == 'rgt_arm_waist':
            if not isinstance(jnt_values, np.ndarray) or jnt_values.size != 7:
                raise ValueError("An 1x7 npdarray must be specified to move a single arm plus the waist!")
            status = update_component(component_name, jnt_values)
            self.base_table.jnts[1]['motion_value'] = jnt_values[0]
            self.base_table.fk()
            the_other_manipulator_name = 'lft_arm' if component_name[:7] == 'rgt_arm' else 'rgt_arm'
            self.manipulator_dict[the_other_manipulator_name].jnts[1]['motion_value'] = jnt_values[0]
            self.manipulator_dict[the_other_manipulator_name].fk()
            return status  # if waist is out of range, the first status will always be out of range
        elif component_name == 'both_arm':
            raise NotImplementedError
        elif component_name == 'all':
            raise NotImplementedError
        else:
            raise ValueError("The given component name is not available!")

    def ik(self,
           component_name,
           tgt_pos,
           tgt_rotmat,
           seed_jnt_values=None,
           tcp_jnt_id=None,
           tcp_loc_pos=None,
           tcp_loc_rotmat=None,
           max_niter=100,
           local_minima="accept",
           toggle_debug=False):
        # if component_name == 'lft_arm' or component_name == 'rgt_arm':
        #     old_tgt_jnts = self.manipulator_dict[component_name].tgtjnts
        #     self.manipulator_dict[component_name].tgtjnts = range(2, self.manipulator_dict[component_name].n_dof + 1)
        #     ik_results = self.manipulator_dict[component_name].ik(tgt_pos,
        #                                                           tgt_rotmat,
        #                                                           seed_jnt_values=seed_jnt_values,
        #                                                           tcp_joint_id=tcp_joint_id,
        #                                                           _loc_flange_pos=_loc_flange_pos,
        #                                                           _loc_flange_rotmat=_loc_flange_rotmat,
        #                                                           max_n_iter=max_n_iter,
        #                                                           policy_for_local_minima=policy_for_local_minima,
        #                                                           toggle_dbg=toggle_dbg)
        #     self.manipulator_dict[component_name].tgtjnts = old_tgt_jnts
        #     return ik_results
        # elif component_name == 'lft_arm_waist' or component_name == 'rgt_arm_waist':
        #     return self.manipulator_dict[component_name].ik(tgt_pos,
        #                                                     tgt_rotmat,
        #                                                     seed_jnt_values=seed_jnt_values,
        #                                                     tcp_joint_id=tcp_joint_id,
        #                                                     _loc_flange_pos=_loc_flange_pos,
        #                                                     _loc_flange_rotmat=_loc_flange_rotmat,
        #                                                     max_n_iter=max_n_iter,
        #                                                     policy_for_local_minima=policy_for_local_minima,
        #                                                     toggle_dbg=toggle_dbg)
        if component_name in ['lft_arm', 'rgt_arm', 'lft_arm_waist', 'rgt_arm_waist']:
            return self.manipulator_dict[component_name].ik(tgt_pos,
                                                            tgt_rotmat,
                                                            seed_jnt_values=seed_jnt_values,
                                                            tcp_joint_id=tcp_jnt_id,
                                                            tcp_loc_pos=tcp_loc_pos,
                                                            tcp_loc_rotmat=tcp_loc_rotmat,
                                                            max_n_iter=max_niter,
                                                            local_minima=local_minima,
                                                            toggle_dbg=toggle_debug)
        elif component_name == 'both_arm':
            raise NotImplementedError
        elif component_name == 'all':
            raise NotImplementedError
        else:
            raise ValueError("The given component name is not available!")

    def get_jnt_values(self, component_name):
        return self.manipulator_dict[component_name].get_jnt_values()

    def is_jnt_values_in_ranges(self, component_name, jnt_values):
        # if component_name == 'lft_arm' or component_name == 'rgt_arm':
        #     old_tgt_jnts = self.manipulator_dict[component_name].tgtjnts
        #     self.manipulator_dict[component_name].tgtjnts = range(2, self.manipulator_dict[component_name].n_dof + 1)
        #     result = self.manipulator_dict[component_name].is_jnt_values_in_ranges(jnt_values)
        #     self.manipulator_dict[component_name].tgtjnts = old_tgt_jnts
        #     return result
        # else:
        return self.manipulator_dict[component_name].are_jnts_in_ranges(jnt_values)

    def rand_conf(self, component_name):
        """
        override robot_interface.rand_conf
        :param component_name:
        :return:
        author: weiwei
        date: 20210406
        """
        if component_name == 'lft_arm' or component_name == 'rgt_arm':
            return super().rand_conf(component_name)[1:]
        elif component_name == 'lft_arm_waist' or component_name == 'rgt_arm_waist':
            return super().rand_conf(component_name)
        elif component_name == 'both_arm':
            return np.hstack((super().rand_conf('lft_arm')[1:], super().rand_conf('rgt_arm')[1:]))
        else:
            raise NotImplementedError

    def hold(self, objcm, jaw_width=None, hnd_name='lft_hnd'):
        """
        the cmodel is added as a part of the robot_s to the cd checker
        :param jaw_width:
        :param objcm:
        :return:
        """
        # if hnd_name == 'lft_hnd':
        #     rel_pos, rel_rotmat = self.lft_arm.cvt_gl_to_loc_tcp(cmodel.get_pos(), cmodel.get_rotmat())
        #     into_list = [self.lft_body.lnks[0],
        #                 self.lft_body.lnks[1],
        #                 self.lft_arm.lnks[1],
        #                 self.lft_arm.lnks[2],
        #                 self.lft_arm.lnks[3],
        #                 self.lft_arm.lnks[4],
        #                 self.rgt_arm.lnks[1],
        #                 self.rgt_arm.lnks[2],
        #                 self.rgt_arm.lnks[3],
        #                 self.rgt_arm.lnks[4],
        #                 self.rgt_arm.lnks[5],
        #                 self.rgt_arm.lnks[6],
        #                 self.rgt_hnd.lft.lnks[0],
        #                 self.rgt_hnd.lft.lnks[1],
        #                 self.rgt_hnd.rgt.lnks[1]]
        #     self.lft_oih_infos.append(self.cc.add_cdobj(cmodel, rel_pos, rel_rotmat, into_list))
        # elif hnd_name == 'rgt_hnd':
        #     rel_pos, rel_rotmat = self.rgt_arm.cvt_gl_to_loc_tcp(cmodel.get_pos(), cmodel.get_rotmat())
        #     into_list = [self.lft_body.lnks[0],
        #                 self.lft_body.lnks[1],
        #                 self.rgt_arm.lnks[1],
        #                 self.rgt_arm.lnks[2],
        #                 self.rgt_arm.lnks[3],
        #                 self.rgt_arm.lnks[4],
        #                 self.lft_arm.lnks[1],
        #                 self.lft_arm.lnks[2],
        #                 self.lft_arm.lnks[3],
        #                 self.lft_arm.lnks[4],
        #                 self.lft_arm.lnks[5],
        #                 self.lft_arm.lnks[6],
        #                 self.lft_hnd.lft.lnks[0],
        #                 self.lft_hnd.lft.lnks[1],
        #                 self.lft_hnd.rgt.lnks[1]]
        #     self.rgt_oih_infos.append(self.cc.add_cdobj(cmodel, rel_pos, rel_rotmat, into_list))
        # else:
        #     raise ValueError("hnd_name must be lft_hnd or rgt_hnd!")
        # if jaw_width is not None:
        #     self.jaw_to(hnd_name, jaw_width)
        # return rel_pos, rel_rotmat

    def get_loc_pose_from_hio(self, hio_pos, hio_rotmat, component_name='lft_arm'):
        """
        get the loc pose of an object from a grasp pose described in an object's local frame
        :param hio_pos: a grasp pose described in an object's local frame -- pos
        :param hio_rotmat: a grasp pose described in an object's local frame -- rotmat
        :return:
        author: weiwei
        date: 20210302
        """
        if component_name == 'lft_arm':
            arm = self.lft_arm
        elif component_name == 'rgt_arm':
            arm = self.rgt_arm
        hnd_pos = arm.jnts[-1]['gl_posq']
        hnd_rotmat = arm.jnts[-1]['gl_rotmatq']
        hnd_homomat = rm.homomat_from_posrot(hnd_pos, hnd_rotmat)
        hio_homomat = rm.homomat_from_posrot(hio_pos, hio_rotmat)
        oih_homomat = rm.homomat_inverse(hio_homomat)
        gl_obj_homomat = hnd_homomat.dot(oih_homomat)
        return self.cvt_gl_to_loc_tcp(component_name, gl_obj_homomat[:3, 3], gl_obj_homomat[:3, :3])

    def get_gl_pose_from_hio(self, hio_pos, hio_rotmat, component_name='lft_arm'):
        """
        get the loc pose of an object from a grasp pose described in an object's local frame
        :param hio_pos: a grasp pose described in an object's local frame -- pos
        :param hio_rotmat: a grasp pose described in an object's local frame -- rotmat
        :return:
        author: weiwei
        date: 20210302
        """
        if component_name == 'lft_arm':
            arm = self.lft_arm
        elif component_name == 'rgt_arm':
            arm = self.rgt_arm
        hnd_pos = arm.jnts[-1]['gl_posq']
        hnd_rotmat = arm.jnts[-1]['gl_rotmatq']
        hnd_homomat = rm.homomat_from_posrot(hnd_pos, hnd_rotmat)
        hio_homomat = rm.homomat_from_posrot(hio_pos, hio_rotmat)
        oih_homomat = rm.homomat_inverse(hio_homomat)
        gl_obj_homomat = hnd_homomat.dot(oih_homomat)
        return gl_obj_homomat[:3, 3], gl_obj_homomat[:3, :3]

    def get_oih_cm_list(self, hnd_name='lft_hnd'):
        """
        oih = object in hand list
        :param hnd_name:
        :return:
        """
        if hnd_name == 'lft_hnd':
            oih_infos = self.lft_oih_infos
        elif hnd_name == 'rgt_hnd':
            oih_infos = self.rgt_oih_infos
        else:
            raise ValueError("hnd_name must be lft_hnd or rgt_hnd!")
        return_list = []
        for obj_info in oih_infos:
            objcm = obj_info['collision_model']
            objcm.set_pos(obj_info['gl_pos'])
            objcm.set_rotmat(obj_info['gl_rotmat'])
            return_list.append(objcm)
        return return_list

    def get_oih_glhomomat_list(self, hnd_name='lft_hnd'):
        """
        oih = object in hand list
        :param hnd_name:
        :return:
        author: weiwei
        date: 20210302
        """
        if hnd_name == 'lft_hnd':
            oih_infos = self.lft_oih_infos
        elif hnd_name == 'rgt_hnd':
            oih_infos = self.rgt_oih_infos
        else:
            raise ValueError("hnd_name must be lft_hnd or rgt_hnd!")
        return_list = []
        for obj_info in oih_infos:
            return_list.append(rm.homomat_from_posrot(obj_info['gl_pos']), obj_info['gl_rotmat'])
        return return_list

    def get_oih_relhomomat(self, objcm, hnd_name='lft_hnd'):
        """
        TODO: useless? 20210320
        oih = object in hand list
        :param objcm
        :param hnd_name:
        :return:
        author: weiwei
        date: 20210302
        """
        if hnd_name == 'lft_hnd':
            oih_info_list = self.lft_oih_infos
        elif hnd_name == 'rgt_hnd':
            oih_info_list = self.rgt_oih_infos
        else:
            raise ValueError("hnd_name must be lft_hnd or rgt_hnd!")
        for obj_info in oih_info_list:
            if obj_info['collision_model'] is objcm:
                return rm.homomat_from_posrot(obj_info['rel_pos']), obj_info['rel_rotmat']

    def release(self, hnd_name, objcm, jaw_width=None):
        """
        the cmodel is added as a part of the robot_s to the cd checker
        :param jaw_width:
        :param objcm:
        :param hnd_name:
        :return:
        """
        if hnd_name == 'lft_hnd':
            oih_infos = self.lft_oih_infos
        elif hnd_name == 'rgt_hnd':
            oih_infos = self.rgt_oih_infos
        else:
            raise ValueError("hnd_name must be lft_hnd or rgt_hnd!")
        if jaw_width is not None:
            self.jaw_to(hnd_name, jaw_width)
        for obj_info in oih_infos:
            if obj_info['collision_model'] is objcm:
                self.cc.delete_cdobj(obj_info)
                oih_infos.remove(obj_info)
                break

    def release_all(self, jaw_width=None, hnd_name='lft_hnd'):
        """
        release all objects from the specified hand
        :param jaw_width:
        :param hnd_name:
        :return:
        author: weiwei
        date: 20210125
        """
        if hnd_name == 'lft_hnd':
            oih_infos = self.lft_oih_infos
        elif hnd_name == 'rgt_hnd':
            oih_infos = self.rgt_oih_infos
        else:
            raise ValueError("hnd_name must be lft_hnd or rgt_hnd!")
        if jaw_width is not None:
            self.jaw_to(hnd_name, jaw_width)
        for obj_info in oih_infos:
            self.cc.delete_cdobj(obj_info)
        oih_infos.clear()

    def gen_stickmodel(self,
                       tcp_jnt_id=None,
                       tcp_loc_pos=None,
                       tcp_loc_rotmat=None,
                       toggle_tcpcs=False,
                       toggle_jntscs=False,
                       toggle_connjnt=False,
                       name='yumi'):
        stickmodel = mc.ModelCollection(name=name)
        self.base_table.gen_stickmodel(tcp_loc_pos=None,
                                         tcp_loc_rotmat=None,
                                         toggle_tcpcs=False,
                                         toggle_jntscs=toggle_jntscs).attach_to(stickmodel)
        self.lft_arm.gen_stickmodel(tcp_jnt_id=tcp_jnt_id,
                                    tcp_loc_pos=tcp_loc_pos,
                                    tcp_loc_rotmat=tcp_loc_rotmat,
                                    toggle_tcp_frame=toggle_tcpcs,
                                    toggle_jnt_frames=toggle_jntscs,
                                    toggle_flange_frame=toggle_connjnt).attach_to(stickmodel)
        # self.lft_hnd.gen_stickmodel(toggle_flange_frame=False,
        #                             toggle_jnt_frames=toggle_jnt_frames,
        #                             toggle_flange_frame=toggle_flange_frame).attach_to(stickmodel)
        self.rgt_arm.gen_stickmodel(tcp_jnt_id=tcp_jnt_id,
                                    tcp_loc_pos=tcp_loc_pos,
                                    tcp_loc_rotmat=tcp_loc_rotmat,
                                    toggle_tcp_frame=toggle_tcpcs,
                                    toggle_jnt_frames=toggle_jntscs,
                                    toggle_flange_frame=toggle_connjnt).attach_to(stickmodel)
        # self.rgt_hnd.gen_stickmodel(toggle_flange_frame=False,
        #                             toggle_jnt_frames=toggle_jnt_frames,
        #                             toggle_flange_frame=toggle_flange_frame).attach_to(stickmodel)
        return stickmodel

    def gen_meshmodel(self,
                      tcp_jnt_id=None,
                      tcp_loc_pos=None,
                      tcp_loc_rotmat=None,
                      toggle_tcpcs=False,
                      toggle_jntscs=False,
                      rgba=None,
                      name='xarm_gripper_meshmodel'):
        meshmodel = mc.ModelCollection(name=name)
        self.base_table.gen_mesh_model(tcp_loc_pos=None,
                                       tcp_loc_rotmat=None,
                                       toggle_tcpcs=False,
                                       toggle_jntscs=toggle_jntscs,
                                       rgba=rgba).attach_to(meshmodel)
        self.lft_arm.gen_meshmodel(tcp_jnt_id=tcp_jnt_id,
                                   tcp_loc_pos=tcp_loc_pos,
                                   tcp_loc_rotmat=tcp_loc_rotmat,
                                   toggle_tcp_frame=toggle_tcpcs,
                                   toggle_jnt_frames=toggle_jntscs,
                                   rgba=rgba).attach_to(meshmodel)
        # self.lft_hnd.gen_meshmodel(toggle_flange_frame=False,
        #                            toggle_jnt_frames=toggle_jnt_frames,
        #                            rgba=rgba).attach_to(meshmodel)
        self.rgt_arm.gen_meshmodel(tcp_jnt_id=tcp_jnt_id,
                                   tcp_loc_pos=tcp_loc_pos,
                                   tcp_loc_rotmat=tcp_loc_rotmat,
                                   toggle_tcp_frame=toggle_tcpcs,
                                   toggle_jnt_frames=toggle_jntscs,
                                   rgba=rgba).attach_to(meshmodel)
        # self.rgt_hnd.gen_meshmodel(toggle_flange_frame=False,
        #                            toggle_jnt_frames=toggle_jnt_frames,
        #                            rgba=rgba).attach_to(meshmodel)
        for obj_info in self.lft_arm.oih_infos:
            objcm = obj_info['collision_model']
            objcm.set_pos(obj_info['gl_pos'])
            objcm.set_rotmat(obj_info['gl_rotmat'])
            objcm.copy().attach_to(meshmodel)
        for obj_info in self.rgt_arm.oih_infos:
            objcm = obj_info['collision_model']
            objcm.set_pos(obj_info['gl_pos'])
            objcm.set_rotmat(obj_info['gl_rotmat'])
            objcm.copy().attach_to(meshmodel)
        return meshmodel


if __name__ == '__main__':
    import time
    import visualization.panda.world as wd
    import modeling.geometric_model as gm
    import basis

    base = wd.World(cam_pos=[5, 3, 4], lookat_pos=[0, 0, 1])
    gm.gen_frame().attach_to(base)
    khibt = KHI_DUAL(enable_cc=True)
    khibt = khibt.gen_meshmodel(toggle_tcpcs=True)
    khibt.attach_to(base)
    base.run()

    # tgt_pos = np.array([.4, 0, .2])
    # tgt_rotmat = rm.rotmat_from_euler(0, math.pi * 2 / 3, -math.pi / 4)
    # ik test
    component_name = 'lft_arm_waist'
    tgt_pos = np.array([-.3, .45, .55])
    tgt_rotmat = rm.rotmat_from_axangle([0, 0, 1], -math.pi / 2)
    # tgt_rotmat = np.eye(3)
    gm.gen_frame(pos=tgt_pos, rotmat=tgt_rotmat).attach_to(base)
    tic = time.time()
    jnt_values = nxt_instance.ik(component_name, tgt_pos, tgt_rotmat, toggle_dbg=True)
    toc = time.time()
    print(toc - tic)
    nxt_instance.fk(component_name, jnt_values)
    nxt_meshmodel = nxt_instance.gen_mesh_model()
    nxt_meshmodel.attach_to(base)
    nxt_instance.gen_stickmodel().attach_to(base)
    # tic = time.time()
    # result = nxt_instance.is_collided()
    # toc = time.time()
    # print(result, toc - tic)
    base.run()

    # hold test
    component_name = 'lft_arm'
    obj_pos = np.array([-.1, .3, .3])
    obj_rotmat = rm.rotmat_from_axangle([0, 1, 0], math.pi / 2)
    objfile = os.path.join(basis.__path__[0], 'objects', 'tubebig.stl')
    objcm = cm.CollisionModel(objfile, cdp_type='cylinder')
    objcm.set_pos(obj_pos)
    objcm.set_rotmat(obj_rotmat)
    objcm.attach_to(base)
    objcm_copy = objcm.copy()
    nxt_instance.hold(objcm=objcm_copy, jaw_width=0.03, hnd_name='lft_hnd')
    tgt_pos = np.array([.4, .5, .4])
    tgt_rotmat = rm.rotmat_from_axangle([0, 1, 0], math.pi / 3)
    jnt_values = nxt_instance.ik(component_name, tgt_pos, tgt_rotmat)
    nxt_instance.fk(component_name, jnt_values)
    # nxt_instance.show_cdprimit()
    nxt_meshmodel = nxt_instance.gen_mesh_model()
    nxt_meshmodel.attach_to(base)

    base.run()
