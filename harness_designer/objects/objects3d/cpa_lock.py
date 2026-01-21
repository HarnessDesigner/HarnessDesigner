if self._is_deleted:
    return


@staticmethod
    def get_cpa_lock_triangles(model):
        if Config.modeling.smooth_cpa_locks:
            return model_to_mesh.get_smooth_triangles(model)
        else:
            return model_to_mesh.get_triangles(model)