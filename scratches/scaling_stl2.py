# load mesh file
street = mesh.Mesh.from_file('../../stls_files/strasen.stl')

figure = plt.figure()
ax = mplot3d.Axes3D(figure)

scale_factor = 4
collection1 = Poly3DCollection(
    street.vectors * scale_factor,
    linewidths=1,
    alpha=0.2
)

street_color = [0.2, 0.5, 0.7]
collection1.set_facecolor(street_color)

ax.add_collection3d(collection1)

# Auto scale to the mesh size
scale1 = street.points.flatten()

ax.auto_scale_xyz(scale1, scale1, scale1)

plt.show()