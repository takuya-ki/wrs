import copy
import numpy as np
import basis.robot_math as rm
import modeling.model_collection as mmc
import modeling.geometric_model as mgm
import robot_sim._kinematics.jlchain as jl
import robot_sim._kinematics.TBD_collision_checker as cc
import robot_sim._kinematics.model_generator as rkmg


# ==============================================
# delays for gl_tcp
# ==============================================

def delay_gl_tcp_decorator(method):
    def wrapper(self, *args, **kwargs):
        self._is_gl_tcp_delayed = True
        return method(self, *args, **kwargs)

    return wrapper


def update_gl_tcp_decorator(method):
    def wrapper(self, *args, **kwargs):
        # print(self._is_geom_delayed)
        if self._is_gl_tcp_delayed:
            self._gl_tcp_pos, self._gl_tcp_rotmat = self.compute_gl_tcp()
            self._is_gl_tcp_delayed = False
        return method(self, *args, **kwargs)

    return wrapper


class ManipulatorInterface(object):

    def __init__(self, pos=np.zeros(3), rotmat=np.eye(3), home_conf=np.zeros(6), name='manipulator'):
        self.name = name
        self.pos = pos
        self.rotmat = rotmat
        # jlc
        self.jlc = jl.JLChain(pos=pos, rotmat=rotmat, n_dof=len(home_conf), name=name)
        self.jlc.home = home_conf
        # tcp is defined locally in flange
        self._loc_tcp_pos = np.zeros(3)
        self._loc_tcp_rotmat = np.eye(3)
        self._is_gl_tcp_delayed = True
        self._gl_tcp_pos = np.zeros(3)
        self._gl_tcp_rotmat = np.eye(3)
        # collision detection
        self.cc = None

    @property
    def jnts(self):
        return self.jlc.jnts

    @property
    def n_dof(self):
        return self.jlc.n_dof

    @property
    def home_conf(self):
        return self.jlc.home

    @property
    def loc_tcp_pos(self):
        return self._loc_tcp_pos

    @loc_tcp_pos.setter
    @delay_gl_tcp_decorator
    def loc_tcp_pos(self, loc_tcp_pos):
        self._loc_tcp_pos = loc_tcp_pos

    @property
    def loc_tcp_rotmat(self):
        return self._loc_tcp_rotmat

    @loc_tcp_rotmat.setter
    @delay_gl_tcp_decorator
    def loc_tcp_rotmat(self, loc_tcp_rotmat):
        self._loc_tcp_rotmat = loc_tcp_rotmat

    @property
    @update_gl_tcp_decorator
    def gl_tcp_pos(self):
        return self._gl_tcp_pos

    @property
    @update_gl_tcp_decorator
    def gl_tcp_rotmat(self):
        return self._gl_tcp_rotmat

    @property
    def jnt_ranges(self):
        return self.jlc.jnt_ranges

    @home_conf.setter
    def home_conf(self, home_conf):
        self.jlc.home = home_conf

    def compute_gl_tcp(self):
        gl_tcp_pos = self.jlc.gl_flange_pos + self.jlc.gl_flange_rotmat @ self._loc_tcp_pos
        gl_tcp_rotmat = self.jlc.gl_flange_rotmat @ self._loc_tcp_rotmat
        return (gl_tcp_pos, gl_tcp_rotmat)

    def goto_given_conf(self, jnt_values):
        return self.fk(jnt_values=jnt_values, toggle_jacobian=False, update=True)

    def goto_home_conf(self):
        return self.goto_given_conf(self.home_conf)

    def fix_to(self, pos, rotmat, jnt_values=None):
        self.jlc.fix_to(pos=pos, rotmat=rotmat, jnt_values=jnt_values)
        self._gl_tcp_pos, self._gl_tcp_rotmat = self.compute_gl_tcp()
        return self.gl_tcp_pos, self.gl_tcp_rotmat

    def fk(self, jnt_values, toggle_jacobian=False, update=False):
        jlc_result = self.jlc.fk(jnt_values=jnt_values, toggle_jacobian=toggle_jacobian, update=update)
        gl_flange_pos = jlc_result[0]
        gl_flange_rotmat = jlc_result[1]
        gl_tcp_pos = gl_flange_pos + gl_flange_rotmat @ self.loc_tcp_pos
        gl_tcp_rotmat = gl_flange_rotmat @ self.loc_tcp_rotmat
        if update:
            self._gl_tcp_pos = gl_tcp_pos
            self._gl_tcp_rotmat = gl_tcp_rotmat
        result = list(jlc_result)
        result[0] = gl_tcp_pos
        result[1] = gl_tcp_rotmat
        return tuple(result)

    def are_jnts_in_ranges(self, jnt_values):
        return self.jlc.are_jnts_in_ranges(jnt_values)

    def get_jnt_values(self):
        return self.jlc.get_jnt_values()

    def rand_conf(self):
        return self.jlc.rand_conf()

    def ik(self,
           tgt_pos: np.ndarray,
           tgt_rotmat: np.ndarray,
           seed_jnt_values=None,
           toggle_dbg=False):
        """
        by default the function calls the numerical implementation of jlc
        override this function in case of analytical IK; ignore the unrequired parameters
        :param tgt_pos:
        :param tgt_rotmat:
        :param seed_jnt_values:
        :param toggle_dbg:
        :return:
        """
        tgt_rotmat = tgt_rotmat @ self.loc_tcp_rotmat.T
        tgt_pos = tgt_pos - tgt_rotmat @ self.loc_tcp_pos
        mgm.gen_frame(pos=tgt_pos, rotmat=tgt_rotmat, alpha=.3).attach_to(base)
        return self.jlc.ik(tgt_pos=tgt_pos,
                           tgt_rotmat=tgt_rotmat,
                           seed_jnt_values=seed_jnt_values,
                           toggle_dbg=toggle_dbg)

    def jacobian(self, jnt_values=None):
        if jnt_values is None:
            j_mat = np.zeros((6, self.jlc.n_dof))
            for i in range(self.jlc.flange_jnt_id + 1):
                if self.jlc.jnts[i].type == rkc.JntType.REVOLUTE:
                    j2t_vec = self.gl_tcp_pos - self.jlc.jnts[i].gl_pos_q
                    j_mat[:3, i] = np.cross(self.jlc.jnts[i].gl_motion_ax, j2t_vec)
                    j_mat[3:6, i] = self.jlc.jnts[i].gl_motion_ax
                if self.jlc.jnts[i].type == rkc.JntType.PRISMATIC:
                    j_mat[:3, i] = self.jlc.jnts[i].gl_motion_ax
            return j_mat
        else:
            homomat = self.jlc.anchor.gl_flange_homomat
            jnt_pos = np.zeros((self.jlc.n_dof, 3))
            jnt_motion_ax = np.zeros((self.jlc.n_dof, 3))
            for i in range(self.jlc.flange_jnt_id + 1):
                jnt_motion_ax[i, :] = homomat[:3, :3] @ self.jlc.jnts[i].loc_motion_ax
                if self.jlc.jnts[i].type == rkc.JntType.REVOLUTE:
                    jnt_pos[i, :] = homomat[:3, 3] + homomat[:3, :3] @ self.jlc.jnts[i].loc_pos
                homomat = homomat @ self.jlc.jnts[i].get_motion_homomat(motion_value=jnt_values[i])
            gl_flange_homomat = homomat @ self.jlc.loc_flange_homomat
            gl_flange_pos = gl_flange_homomat[:3, 3]
            gl_flange_rotmat = gl_flange_homomat[:3, :3]
            gl_tcp_pos = gl_flange_pos + gl_flange_rotmat @ self.loc_tcp_pos
            j_mat = np.zeros((6, self.jlc.n_dof))
            for i in range(self.jlc.flange_jnt_id + 1):
                if self.jlc.jnts[i].type == rkc.JntType.REVOLUTE:
                    j2t_vec = gl_tcp_pos - jnt_pos[i, :]
                    j_mat[:3, i] = np.cross(jnt_motion_ax[i, :], j2t_vec)
                    j_mat[3:6, i] = jnt_motion_ax[i, :]
                if self.jlc.jnts[i].type == rkc.JntType.PRISMATIC:
                    j_mat[:3, i] = jnt_motion_ax[i, :]
            return j_mat

    def manipulability_val(self):
        j_mat = self.jacobian()
        return np.sqrt(np.linalg.det(j_mat @ j_mat.T))

    def manipulability_mat(self):
        j_mat = self.jacobian()
        # linear ellipsoid
        linear_j_dot_jt = j_mat[:3, :] @ j_mat[:3, :].T
        eig_values, eig_vecs = np.linalg.eig(linear_j_dot_jt)
        linear_ellipsoid_mat = np.eye(3)
        linear_ellipsoid_mat[:, 0] = np.sqrt(eig_values[0]) * eig_vecs[:, 0]
        linear_ellipsoid_mat[:, 1] = np.sqrt(eig_values[1]) * eig_vecs[:, 1]
        linear_ellipsoid_mat[:, 2] = np.sqrt(eig_values[2]) * eig_vecs[:, 2]
        # angular ellipsoid
        angular_j_dot_jt = j_mat[3:, :] @ j_mat[3:, :].T
        eig_values, eig_vecs = np.linalg.eig(angular_j_dot_jt)
        angular_ellipsoid_mat = np.eye(3)
        angular_ellipsoid_mat[:, 0] = np.sqrt(eig_values[0]) * eig_vecs[:, 0]
        angular_ellipsoid_mat[:, 1] = np.sqrt(eig_values[1]) * eig_vecs[:, 1]
        angular_ellipsoid_mat[:, 2] = np.sqrt(eig_values[2]) * eig_vecs[:, 2]
        return (linear_ellipsoid_mat, angular_ellipsoid_mat)

    def cvt_pose_in_tcp_to_gl(self, loc_pos=np.zeros(3), loc_rotmat=np.eye(3)):
        gl_pos = self.gl_tcp_pos + self.gl_tcp_rotmat.dot(loc_pos)
        gl_rotmat = self.gl_tcp_rotmat.dot(loc_rotmat)
        return (gl_pos, gl_rotmat)

    def cvt_gl_to_tcp(self, gl_pos, gl_rotmat):
        return rm.rel_pose(self.gl_tcp_pos, self.gl_tcp_rotmat, gl_pos, gl_rotmat)

    def is_collided(self, obstacle_list=[], otherrobot_list=[]):
        """
        Interface for "is cdprimit collided", must be implemented in child class
        :param obstacle_list:
        :param otherrobot_list:
        :return:
        author: weiwei
        date: 20201223
        """
        return self.cc.is_collided(obstacle_list=obstacle_list,
                                   otherrobot_list=otherrobot_list)

    def show_cdprimit(self):
        self.cc.show_cdprim()

    def unshow_cdprimit(self):
        self.cc.unshow_cdprim()

    def gen_meshmodel(self,
                      rgb=None,
                      alpha=None,
                      toggle_tcp_frame=True,
                      toggle_jnt_frames=False,
                      toggle_flange_frame=False,
                      toggle_cdprim=False,
                      toggle_cdmesh=False,
                      name="manipulator_mesh"):
        m_col = rkmg.gen_jlc_mesh(self.jlc,
                                  rgb=rgb,
                                  alpha=alpha,
                                  toggle_jnt_frames=toggle_jnt_frames,
                                  toggle_flange_frame=toggle_flange_frame,
                                  toggle_cdprim=toggle_cdprim,
                                  toggle_cdmesh=toggle_cdmesh,
                                  name=name)
        if toggle_tcp_frame:
            rkmg.gen_indicated_frame(spos=self.jlc.gl_flange_pos, gl_pos=self.gl_tcp_pos,
                                     gl_rotmat=self.gl_tcp_rotmat).attach_to(m_col)
        return m_col

    def gen_stickmodel(self,
                       toggle_tcp_frame=False,
                       toggle_jnt_frames=False,
                       toggle_flange_frame=False,
                       name="manipulator_stickmodel"):
        m_col = rkmg.gen_jlc_stick(self.jlc,
                                   toggle_jnt_frames=toggle_jnt_frames,
                                   toggle_flange_frame=toggle_flange_frame,
                                   name=name)
        if toggle_tcp_frame:
            rkmg.gen_indicated_frame(spos=self.jlc.gl_flange_pos, gl_pos=self._gl_tcp_pos,
                                     gl_rotmat=self._gl_tcp_rotmat).attach_to(m_col)
        return m_col

    def gen_endsphere(self):
        return mgm.gen_sphere(pos=self.gl_tcp_pos)

    def enable_cc(self):
        self.cc = cc.CollisionChecker("collision_checker")

    def disable_cc(self):
        """
        clear pairs and pdndp
        :return:
        """
        for cdelement in self.cc.cce_dict:
            cdelement['cdprimit_childid'] = -1
        self.cc = None
        # self.cc.cce_dict = []
        # for child in self.cc.np.getChildren():
        #     child.removeNode()
        # self.cc.nbitmask = 0

    def copy(self):
        self_copy = copy.deepcopy(self)
        # deepcopying colliders are problematic, I have to update it manually
        if self.cc is not None:
            for child in self_copy.cc.np.getChildren():  # empty NodePathCollection if the np does not have a child
                self_copy.cc.cd_trav.addCollider(child, self_copy.cc.cd_handler)
        return self_copy
