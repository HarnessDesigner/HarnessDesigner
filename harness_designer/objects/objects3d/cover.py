if self._is_deleted:
    return


@staticmethod
    def get_cover_triangles(model):
        if Config.modeling.smooth_covers:
            return model_to_mesh.get_smooth_triangles(model)
        else:
            return model_to_mesh.get_triangles(model)