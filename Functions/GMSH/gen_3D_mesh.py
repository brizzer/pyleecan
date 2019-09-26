from numpy import pi
from pyleecan.Classes.Arc import Arc
import sys
import gmsh


def gen_3D_mesh(lamination, save_path="Lamination.msh", mesh_size=5e-3, Nlayer=20):
    """Draw 3D mesh of the lamination
    Parameters
    ----------
    lamination: LamSlot
        Lamintation with slot to draw
    save_path: str
        Path to save the msh result file
    mesh_size : float
        Size of the mesh [m]
    Nlayer : int
        Number of mesh layer on Z axis

    Returns
    -------
    None
    """
    tooth_surf = lamination.slot.get_surface_tooth()

    # For readibility
    model = gmsh.model
    factory = model.geo
    L = lamination.L1  # Lamination length
    Zs = lamination.slot.Zs

    # Start a new model
    gmsh.initialize(sys.argv)
    gmsh.option.setNumber("General.Terminal", 1)
    model.add("Pyleecan")

    # Create all the points of the tooth
    NPoint = 0  # Number of point created
    for line in tooth_surf.get_lines():
        Z = line.get_begin()
        NPoint += 1
        factory.addPoint(Z.real, Z.imag, -L / 2, mesh_size, NPoint)

    # Draw all the lines of the tooth
    NLine = 0  # Number of line created
    for line in tooth_surf.get_lines():
        NLine += 1
        if NLine == len(tooth_surf.get_lines()):
            if isinstance(line, Arc):
                Zc = line.get_center()
                NPoint += 1
                factory.addPoint(Zc.real, Zc.imag, -L / 2, mesh_size, NPoint)
                factory.addCircleArc(NLine, NPoint - 1, 1, NLine)
            else:
                factory.addLine(NLine, 1, NLine)
        else:
            if isinstance(line, Arc):
                Zc = line.get_center()
                NPoint += 1
                factory.addPoint(Zc.real, Zc.imag, -L / 2, mesh_size, NPoint)
                factory.addCircleArc(NLine, NPoint, NLine + 1, NLine)
            else:
                factory.addLine(NLine, NLine + 1, NLine)

    # Create the Tooth surface
    gmsh.model.geo.addCurveLoop(list(range(1, NLine + 1)), 1)
    gmsh.model.geo.addPlaneSurface([1], 1)
    gmsh.model.addPhysicalGroup(2, [1], 1)
    gmsh.model.setPhysicalName(2, 1, "Tooth")

    # Copy/Rotate all the tooth to get the 2D lamination
    surf_list = [1]
    for ii in range(Zs):
        ov = factory.copy([(2, 1)])
        factory.rotate(ov, 0, 0, -L / 2, 0, 0, 1, (ii + 1) * 2 * pi / 36)
        surf_list.append(ov[0][1])
    gmsh.model.addPhysicalGroup(2, surf_list, 2)
    gmsh.model.setPhysicalName(2, 2, "Lamination")

    # Extrude the lamination
    for surf in surf_list:
        ov = factory.extrude([(2, surf)], 0, 0, L, numElements=[Nlayer])
    model.addPhysicalGroup(3, list(range(1, Zs + 1)), 1)
    if lamination.is_stator:
        model.setPhysicalName(3, 1, "stator")
    else:
        model.setPhysicalName(3, 1, "rotor")

    # Generate the 3D mesh
    factory.synchronize()
    gmsh.model.mesh.generate(3)

    # Save and close
    gmsh.write(save_path)
    gmsh.finalize()