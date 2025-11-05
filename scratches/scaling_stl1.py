import openstl
import numpy as np

model = openstl.read("model.stl")  # np.array of shape (N,4,3) -> normal, v0,v1,v2

scale = 1000.0
model[:,1:4,:] *= scale # Avoid scaling normals

openstl.write("scaled_model.stl", model, openstl.format.binary)