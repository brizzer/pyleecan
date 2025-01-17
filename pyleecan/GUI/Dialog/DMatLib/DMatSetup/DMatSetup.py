from os.path import join, dirname, isfile
from PySide2.QtWidgets import QDialog, QMessageBox, QLayout
from PySide2.QtCore import Qt, Signal
from logging import getLogger
from numpy import pi, array, array_equal

from .....GUI.Dialog.DMatLib.DMatSetup.Gen_DMatSetup import Gen_DMatSetup
from .....Classes.Material import Material
from .....Classes.ImportMatrixVal import ImportMatrixVal
from .....Classes.ImportMatrix import ImportMatrix
from .....Classes.ImportMatrixXls import ImportMatrixXls
from .....Functions.path_tools import rel_file_path
from .....loggers import GUI_LOG_NAME


class DMatSetup(Gen_DMatSetup, QDialog):
    # Signal to DMatLib to update material treeview
    saveNeededChanged = Signal()  # Modified / Saved / Canceled (add/remove *)
    materialToDelete = Signal()  # Material will be deleted in DMatLib
    materialToRename = Signal()  # Material name/path has changed => rename in DMatLib
    materialToRevert = Signal()  # Revert reference from DMatLib
    materialToSave = Signal()  # Material to save (update reference/file/machine)

    def __init__(self, parent=None, material=None):
        """Dialog for edit/show material properties

        Parameters
        ----------
        material : Material
            material to edit
        parent : Widget
            Parent Widget (DMatLib)
        material : Material
            Material object to show/edit
        """
        # Build the interface according to the .ui file
        QDialog.__init__(self)
        self.setupUi(self)

        self.is_save_needed = False
        self.init_name = None  # Initial name of current Material (to revert rename)
        self.init_path = None  # Initial part of current Material (for rename)
        self.mat = None  # Current material being edited

        # Set initial material
        if material is not None:
            self.set_material(material=material)

        # === setup signals ===
        # General
        self.le_name.editingFinished.connect(self.set_name)
        self.cb_material_type.currentIndexChanged.connect(self.set_is_isotropic)
        # Elec
        self.lf_rho_elec.editingFinished.connect(self.set_rho_elec)
        # Magnetics
        self.lf_mur_lin.editingFinished.connect(self.set_mur_lin)
        self.lf_Brm20.editingFinished.connect(self.set_Brm20)
        self.lf_alpha_Br.editingFinished.connect(self.set_alpha_Br)
        self.lf_Wlam.editingFinished.connect(self.set_Wlam)
        # Economical
        self.lf_cost_unit.editingFinished.connect(self.set_cost_unit)
        # Thermics
        self.lf_Cp.editingFinished.connect(self.set_Cp)
        self.lf_alpha.editingFinished.connect(self.set_alpha)
        self.lf_L.editingFinished.connect(self.set_lambda)
        self.lf_Lx.editingFinished.connect(self.set_lambda_x)
        self.lf_Ly.editingFinished.connect(self.set_lambda_y)
        self.lf_Lz.editingFinished.connect(self.set_lambda_z)
        # Mechanics
        self.lf_rho_meca.editingFinished.connect(self.set_rho_meca)
        self.lf_E.editingFinished.connect(self.set_E)
        self.lf_Ex.editingFinished.connect(self.set_Ex)
        self.lf_Ey.editingFinished.connect(self.set_Ey)
        self.lf_Ez.editingFinished.connect(self.set_Ez)
        self.lf_G.editingFinished.connect(self.set_G)
        self.lf_Gxy.editingFinished.connect(self.set_Gxy)
        self.lf_Gxz.editingFinished.connect(self.set_Gxz)
        self.lf_Gyz.editingFinished.connect(self.set_Gyz)
        self.lf_nu.editingFinished.connect(self.set_nu)
        self.lf_nu_xy.editingFinished.connect(self.set_nu_xy)
        self.lf_nu_xz.editingFinished.connect(self.set_nu_xz)
        self.lf_nu_yz.editingFinished.connect(self.set_nu_yz)
        self.tab_values.saveNeeded.connect(self.set_table_values)
        self.c_type_material.currentIndexChanged.connect(self.change_type_material)

        # Connect buttons
        self.b_delete.clicked.connect(lambda: self.materialToDelete.emit())
        self.b_save.clicked.connect(lambda: self.materialToSave.emit())
        self.b_cancel.clicked.connect(lambda: self.materialToRevert.emit())

    def set_save_needed(self, is_save_needed=True):
        """Set if there are unsaved modifications within the object

        Parameters
        ----------
        self : DMatSetup
            A DMatSetup object
        is_save_needed : bool
            New value for is_save_needed
        """
        old = self.is_save_needed  # Keep old values

        self.is_save_needed = is_save_needed
        self.b_save.setEnabled(is_save_needed)
        self.b_cancel.setEnabled(is_save_needed)

        if is_save_needed != old:
            # Raise signal only if value is different
            getLogger(GUI_LOG_NAME).debug("DMatSetup: Sending saveNeededChanged")
            self.saveNeededChanged.emit()

    def set_material(self, material, is_save_needed=False):
        """Update the current material and setup all the widgets

        Parameters
        ----------
        self : DMatSetup
            A DMatSetup object
        material : Material
            The material to edit/show
        is_save_needed : bool
            True if the material is different from the reference
        """
        old_mat = self.mat
        self.mat = material
        self.init_name = self.mat.name  # Keep to revert rename
        self.init_path = self.mat.path
        getLogger(GUI_LOG_NAME).debug("DMatSetup: Setting material " + self.mat.name)

        self.le_name.setText(self.mat.name)
        if self.mat.is_isotropic:
            self.cb_material_type.setCurrentIndex(1)
        else:
            self.cb_material_type.setCurrentIndex(0)

        # === check material attribute and set values ===
        # Elec
        if self.mat.elec is None:
            self.set_default("elec")
        self.lf_rho_elec.setValue(self.mat.elec.rho)

        # Economical
        if self.mat.eco is None:
            self.set_default("eco")
        self.lf_cost_unit.setValue(self.mat.eco.cost_unit)

        # Thermics
        if self.mat.HT is None:
            self.set_default("HT")
        self.lf_Cp.setValue(self.mat.HT.Cp)
        self.lf_alpha.setValue(self.mat.HT.alpha)
        self.lf_L.setValue(self.mat.HT.lambda_x)
        self.lf_Lx.setValue(self.mat.HT.lambda_x)
        self.lf_Ly.setValue(self.mat.HT.lambda_y)
        self.lf_Lz.setValue(self.mat.HT.lambda_z)
        # Structural
        if self.mat.struct is None:
            self.set_default("struct")
        self.lf_rho_meca.setValue(self.mat.struct.rho)

        if self.mat.struct.Ex not in [0, None]:
            self.lf_E.setValue(self.mat.struct.Ex / 1e9)
            self.lf_Ex.setValue(self.mat.struct.Ex / 1e9)
        else:
            self.lf_E.setValue(self.mat.struct.Ex)
            self.lf_Ex.setValue(self.mat.struct.Ex)
        if self.mat.struct.Ey not in [0, None]:
            self.lf_Ey.setValue(self.mat.struct.Ey / 1e9)
        else:
            self.lf_Ey.setValue(self.mat.struct.Ey)
        if self.mat.struct.Ez not in [0, None]:
            self.lf_Ez.setValue(self.mat.struct.Ez / 1e9)
        else:
            self.lf_Ez.setValue(self.mat.struct.Ez)
        if self.mat.struct.Gxy not in [0, None]:
            self.lf_G.setValue(self.mat.struct.Gxy / 1e9)
            self.lf_Gxy.setValue(self.mat.struct.Gxy / 1e9)
        else:
            self.lf_G.setValue(self.mat.struct.Gxy)
            self.lf_Gxy.setValue(self.mat.struct.Gxy)
        if self.mat.struct.Gxz not in [0, None]:
            self.lf_Gxz.setValue(self.mat.struct.Gxz / 1e9)
        else:
            self.lf_Gxz.setValue(self.mat.struct.Gxz)
        if self.mat.struct.Gyz not in [0, None]:
            self.lf_Gyz.setValue(self.mat.struct.Gyz / 1e9)
        else:
            self.lf_Gyz.setValue(self.mat.struct.Gyz)
        self.lf_nu.setValue(self.mat.struct.nu_xy)
        self.lf_nu_xy.setValue(self.mat.struct.nu_xy)
        self.lf_nu_xz.setValue(self.mat.struct.nu_xz)
        self.lf_nu_yz.setValue(self.mat.struct.nu_yz)

        # Magnetical
        if self.mat.mag is None:
            self.set_default("mag")

        self.lf_mur_lin.setValue(self.mat.mag.mur_lin)
        self.lf_Brm20.setValue(self.mat.mag.Brm20)
        self.lf_alpha_Br.setValue(self.mat.mag.alpha_Br)
        self.lf_Wlam.setValue(self.mat.mag.Wlam)
        # Setup tab values
        if not isinstance(self.mat.mag.BH_curve, ImportMatrixVal):
            self.g_BH_import.setChecked(False)
        elif array_equal(self.mat.mag.BH_curve.value, array([[0, 0]])):
            self.g_BH_import.setChecked(False)
        else:
            self.g_BH_import.setChecked(True)
        self.tab_values.setWindowFlags(self.tab_values.windowFlags() & ~Qt.Dialog)
        self.tab_values.title = self.g_BH_import.title()
        self.tab_values.N_row_txt = "Nb of Points"
        self.tab_values.shape_max = (None, 2)
        self.tab_values.shape_min = (None, 2)
        self.tab_values.col_header = ["H-curve(A/m)", "B-curve(T)"]
        self.tab_values.unit_order = ["First column H", "First column B"]
        self.tab_values.button_plot_title = "B(H)"
        self.tab_values.si_col.hide()
        self.tab_values.in_col.hide()
        self.tab_values.b_close.hide()
        self.tab_values.b_import.setHidden(False)
        self.tab_values.b_export.setHidden(False)

        if isinstance(self.mat.mag.BH_curve, ImportMatrixXls):
            self.mat.mag.BH_curve = ImportMatrixVal(self.mat.mag.BH_curve.get_data())
            self.tab_values.data = self.mat.mag.BH_curve.get_data()
        elif not isinstance(self.mat.mag.BH_curve, ImportMatrixVal):
            self.tab_values.data = array([[0, 0]])
        elif self.mat.mag.BH_curve.get_data() is not None:
            self.tab_values.data = self.mat.mag.BH_curve.get_data()
        else:
            self.tab_values.data = array([[0, 0]])
        self.tab_values.update()

        if isinstance(self.mat.mag.BH_curve, ImportMatrixVal) and not array_equal(
            self.mat.mag.BH_curve.value, array([[0, 0]])
        ):
            self.c_type_material.setCurrentIndex(2)
        elif self.mat.mag.Brm20 != 0 and self.mat.mag.alpha_Br != 0:
            self.c_type_material.setCurrentIndex(1)
        else:
            self.c_type_material.setCurrentIndex(0)
        self.change_type_material()

        # Hide useless widget
        self.in_epsr.hide()
        self.lf_epsr.hide()
        self.unit_epsr.hide()
        # Enable/Disable buttons
        self.blockSignals(True)
        self.set_save_needed(is_save_needed=is_save_needed)
        self.blockSignals(False)

    def set_default(self, attr):
        """When mat.elec or mat.mag are None, initialize with default values

        Parameters
        ----------
        self : DMatSetup
            A DMatSetup widget
        attr : str
            name of the property to set
        """
        setattr(self.mat, attr, type(getattr(Material(), attr))())

    def set_name(self):
        """Signal to update the value of name according to the line edit

        Parameters
        ----------
        self : DMatSetup
            A DMatSetup object
        """

        file_name = str(self.le_name.text())
        if file_name == self.init_name:
            return  # New name is the same as the previous one

        # Check that the user wants to rename the materials
        msg = self.tr(
            "Do you want to rename your material to "
            + file_name
            + " ?\nAll current modifications (if any) on the material will be saved."
        )
        reply = QMessageBox.question(
            self,
            self.tr("Renaming material"),
            msg,
            QMessageBox.Yes,
            QMessageBox.No,
        )
        self.qmessagebox_question = reply
        if reply == QMessageBox.No:
            # Revert name
            self.le_name.blockSignals(True)
            self.le_name.setText(self.init_name)
            self.le_name.blockSignals(False)
            return

        # Check that new name is correct (doesn't exist)
        filepath = rel_file_path(
            join(dirname(self.mat.path), file_name + ".json"), "MATLIB_DIR"
        )
        if isfile(filepath):
            QMessageBox().critical(
                self,
                self.tr("Error"),
                self.tr(
                    "A material with the name "
                    + file_name
                    + " already exist!\nPlease enter another name."
                ),
            )
            # Revert name
            self.le_name.blockSignals(True)
            self.le_name.setText(self.init_name)
            self.le_name.blockSignals(False)
            return

        # Update name and path
        self.mat.name = file_name
        self.le_name.setText(self.mat.name)
        self.mat.path = rel_file_path(
            join(dirname(self.mat.path), file_name + ".json"), "MATLIB_DIR"
        )
        self.set_save_needed(is_save_needed=False)
        self.materialToRename.emit()  # Update reference and treeview

    def set_is_isotropic(self):
        """Signal to update the value of is_isotropic according to the checkbox

        Parameters
        ----------
        self :
            A DMatSetup object
        is_checked :
            State of the checkbox

        Returns
        -------
        None
        """
        if self.cb_material_type.currentText() == "Isotropic":
            self.mat.is_isotropic = True
            self.nav_meca.setCurrentIndex(1)
            self.nav_ther.setCurrentIndex(1)
        elif self.cb_material_type.currentText() == "Orthotropic":
            self.mat.is_isotropic = False
            self.nav_meca.setCurrentIndex(0)
            self.nav_ther.setCurrentIndex(0)

        self.set_save_needed(is_save_needed=True)

    def set_rho_elec(self):
        """Signal to update the value of rho_elec according to the line edit

        Parameters
        ----------
        self :
            A DMatSetup object

        Returns
        -------
        None
        """
        if self.mat.elec.rho != self.lf_rho_elec.value():
            self.mat.elec.rho = self.lf_rho_elec.value()
            self.set_save_needed(is_save_needed=True)

    def set_mur_lin(self):
        """Signal to update the value of mur_lin according to the line edit

        Parameters
        ----------
        self :
            A DMatSetup object

        Returns
        -------
        None
        """
        if self.mat.mag.mur_lin != self.lf_mur_lin.value():
            self.mat.mag.mur_lin = self.lf_mur_lin.value()

            self.set_save_needed(is_save_needed=True)

    def set_Brm20(self):
        """Signal to update the value of Brm20 according to the line edit

        Parameters
        ----------
        self :
            A DMatSetup object

        Returns
        -------
        None
        """
        if self.mat.mag.Brm20 != self.lf_Brm20.value():
            self.mat.mag.Brm20 = self.lf_Brm20.value()

            self.set_save_needed(is_save_needed=True)

    def set_alpha_Br(self):
        """Signal to update the value of alpha_Br according to the line edit

        Parameters
        ----------
        self :
            A DMatSetup object

        Returns
        -------
        None
        """
        if self.mat.mag.alpha_Br != self.lf_alpha_Br.value():
            self.mat.mag.alpha_Br = self.lf_alpha_Br.value()
            self.set_save_needed(is_save_needed=True)

    def set_Wlam(self):
        """Signal to update the value of Wlam according to the line edit

        Parameters
        ----------
        self :
            A DMatSetup object

        Returns
        -------
        None
        """
        if self.mat.mag.Wlam != self.lf_Wlam.value():
            self.mat.mag.Wlam = self.lf_Wlam.value()
            self.set_save_needed(is_save_needed=True)

    def set_cost_unit(self):
        """Signal to update the value of cost_unit according to the line edit

        Parameters
        ----------
        self :
            A DMatSetup object

        Returns
        -------
        None
        """
        if self.mat.eco.cost_unit != self.lf_cost_unit.value():
            self.mat.eco.cost_unit = self.lf_cost_unit.value()
            self.set_save_needed(is_save_needed=True)

    def set_Cp(self):
        """Signal to update the value of Cp according to the line edit

        Parameters
        ----------
        self :
            A DMatSetup object

        Returns
        -------
        None
        """
        if self.mat.HT.Cp != self.lf_Cp.value():
            self.mat.HT.Cp = self.lf_Cp.value()
            self.set_save_needed(is_save_needed=True)

    def set_alpha(self):
        """Signal to update the value of alpha according to the line edit

        Parameters
        ----------
        self :
            A DMatSetup object

        Returns
        -------
        None
        """
        if self.mat.HT.alpha != self.lf_alpha.value():
            self.mat.HT.alpha = self.lf_alpha.value()
            self.set_save_needed(is_save_needed=True)

    def set_lambda(self):
        """Signal to update the value of lambda according to the line edit

        Parameters
        ----------
        self :
            A DMatSetup object

        Returns
        -------
        None
        """
        if self.mat.HT.lambda_x != self.lf_L.value():
            self.mat.HT.lambda_x = self.lf_L.value()
            self.mat.HT.lambda_y = self.lf_L.value()
            self.mat.HT.lambda_z = self.lf_L.value()
            self.set_save_needed(is_save_needed=True)

    def set_lambda_x(self):
        """Signal to update the value of lambda_x according to the line edit

        Parameters
        ----------
        self :
            A DMatSetup object

        Returns
        -------
        None
        """
        if self.mat.HT.lambda_x != self.lf_Lx.value():
            self.mat.HT.lambda_x = self.lf_Lx.value()
            self.set_save_needed(is_save_needed=True)

    def set_lambda_y(self):
        """Signal to update the value of lambda_y according to the line edit

        Parameters
        ----------
        self :
            A DMatSetup object

        Returns
        -------
        None
        """
        if self.mat.HT.lambda_y != self.lf_Ly.value():
            self.mat.HT.lambda_y = self.lf_Ly.value()
            self.set_save_needed(is_save_needed=True)

    def set_lambda_z(self):
        """Signal to update the value of lambda_z according to the line edit

        Parameters
        ----------
        self :
            A DMatSetup object

        Returns
        -------
        None
        """
        if self.mat.HT.lambda_z != self.lf_Lz.value():
            self.mat.HT.lambda_z = self.lf_Lz.value()
            self.set_save_needed(is_save_needed=True)

    def set_rho_meca(self):
        """Signal to update the value of rho_meca according to the line edit

        Parameters
        ----------
        self :
            A DMatSetup object

        Returns
        -------
        None
        """
        if self.mat.struct.rho != self.lf_rho_meca.value():
            self.mat.struct.rho = self.lf_rho_meca.value()
            self.set_save_needed(is_save_needed=True)

    def set_E(self):
        """Signal to update the value of Ex according to the line edit

        Parameters
        ----------
        self :
            A DMatSetup object

        Returns
        -------
        None
        """
        if self.mat.struct.Ex != self.lf_E.value() * 1e9:
            self.mat.struct.Ex = self.lf_E.value() * 1e9
            self.mat.struct.Ey = self.lf_E.value() * 1e9
            self.mat.struct.Ez = self.lf_E.value() * 1e9
            self.set_save_needed(is_save_needed=True)

    def set_Ex(self):
        """Signal to update the value of Ex according to the line edit

        Parameters
        ----------
        self :
            A DMatSetup object

        Returns
        -------
        None
        """
        if self.mat.struct.Ex != self.lf_Ex.value() * 1e9:
            self.mat.struct.Ex = self.lf_Ex.value() * 1e9
            self.set_save_needed(is_save_needed=True)

    def set_Ey(self):
        """Signal to update the value of Ey according to the line edit

        Parameters
        ----------
        self :
            A DMatSetup object

        Returns
        -------
        None
        """
        if self.mat.struct.Ey != self.lf_Ey.value() * 1e9:
            self.mat.struct.Ey = self.lf_Ey.value() * 1e9
            self.set_save_needed(is_save_needed=True)

    def set_Ez(self):
        """Signal to update the value of Ez according to the line edit

        Parameters
        ----------
        self :
            A DMatSetup object

        Returns
        -------
        None
        """
        if self.mat.struct.Ez != self.lf_Ez.value() * 1e9:
            self.mat.struct.Ez = self.lf_Ez.value() * 1e9
            self.set_save_needed(is_save_needed=True)

    def set_G(self):
        """Signal to update the value of G according to the line edit

        Parameters
        ----------
        self :
            A DMatSetup object

        Returns
        -------
        None
        """
        if self.mat.struct.Gxy != self.lf_G.value() * 1e9:
            self.mat.struct.Gxy = self.lf_G.value() * 1e9
            self.mat.struct.Gxz = self.lf_G.value() * 1e9
            self.mat.struct.Gyz = self.lf_G.value() * 1e9
            self.set_save_needed(is_save_needed=True)

    def set_Gxy(self):
        """Signal to update the value of Gxy according to the line edit

        Parameters
        ----------
        self :
            A DMatSetup object

        Returns
        -------
        None
        """
        if self.mat.struct.Gxy != self.lf_Gxy.value() * 1e9:
            self.mat.struct.Gxy = self.lf_Gxy.value() * 1e9
            self.set_save_needed(is_save_needed=True)

    def set_Gxz(self):
        """Signal to update the value of Gxz according to the line edit

        Parameters
        ----------
        self :
            A DMatSetup object

        Returns
        -------
        None
        """
        if self.mat.struct.Gxz != self.lf_Gxz.value() * 1e9:
            self.mat.struct.Gxz = self.lf_Gxz.value() * 1e9
            self.set_save_needed(is_save_needed=True)

    def set_Gyz(self):
        """Signal to update the value of Gyz according to the line edit

        Parameters
        ----------
        self :
            A DMatSetup object

        Returns
        -------
        None
        """
        if self.mat.struct.Gyz != self.lf_Gyz.value() * 1e9:
            self.mat.struct.Gyz = self.lf_Gyz.value() * 1e9
            self.set_save_needed(is_save_needed=True)

    def set_nu(self):
        """Signal to update the value of nu_xy according to the line edit

        Parameters
        ----------
        self :
            A DMatSetup object

        Returns
        -------
        None
        """
        if self.mat.struct.nu_xy != self.lf_nu.value():
            self.mat.struct.nu_xy = self.lf_nu.value()
            self.mat.struct.nu_xz = self.lf_nu.value()
            self.mat.struct.nu_yz = self.lf_nu.value()
            self.set_save_needed(is_save_needed=True)

    def set_nu_xy(self):
        """Signal to update the value of nu_xy according to the line edit

        Parameters
        ----------
        self :
            A DMatSetup object

        Returns
        -------
        None
        """
        if self.mat.struct.nu_xy != self.lf_nu_xy.value():
            self.mat.struct.nu_xy = self.lf_nu_xy.value()
            self.set_save_needed(is_save_needed=True)

    def set_nu_xz(self):
        """Signal to update the value of nu_xz according to the line edit

        Parameters
        ----------
        self :
            A DMatSetup object

        Returns
        -------
        None
        """
        if self.mat.struct.nu_xz != self.lf_nu_xz.value():
            self.mat.struct.nu_xz = self.lf_nu_xz.value()
            self.set_save_needed(is_save_needed=True)

    def set_nu_yz(self):
        """Signal to update the value of nu_yz according to the line edit

        Parameters
        ----------
        self :
            A DMatSetup object

        Returns
        -------
        None
        """
        if self.mat.struct.nu_yz != self.lf_nu_yz.value():
            self.mat.struct.nu_yz = self.lf_nu_yz.value()
            self.set_save_needed(is_save_needed=True)

    def set_table_values(self):
        """Signal to update the value of the table according to the table

        Parameters
        ----------
        self :
            A DMatSetup object

        Returns
        -------
        None
        """
        if isinstance(self.mat.mag.BH_curve, ImportMatrixVal):
            if not array_equal(self.mat.mag.BH_curve.value, self.tab_values.get_data()):
                self.mat.mag.BH_curve.value = self.tab_values.get_data()
                self.set_save_needed(is_save_needed=True)
        elif isinstance(self.mat.mag.BH_curve, (ImportMatrixXls, ImportMatrix)):
            self.mat.mag.BH_curve = ImportMatrixVal(self.tab_values.get_data())
            self.set_save_needed(is_save_needed=True)

    def change_type_material(self):
        """Hide or show units that need to be defined depending on the type of the material
        Parameters
        ----------
        self :
            A DMatSetup object

        Returns
        -------
        None
        """

        if self.c_type_material.currentIndex() == 0:  # Linear
            self.in_Brm20.setHidden(True)
            self.lf_Brm20.setHidden(True)
            self.unit_Brm20.setHidden(True)
            self.in_alpha_Br.setHidden(True)
            self.lf_alpha_Br.setHidden(True)
            self.unit_alpha_Br.setHidden(True)
            self.nav_mag.setCurrentIndex(0)

        elif self.c_type_material.currentIndex() == 1:  # Magnetic
            self.in_Brm20.setHidden(False)
            self.lf_Brm20.setHidden(False)
            self.unit_Brm20.setHidden(False)
            self.in_alpha_Br.setHidden(False)
            self.lf_alpha_Br.setHidden(False)
            self.unit_alpha_Br.setHidden(False)
            self.nav_mag.setCurrentIndex(0)

        else:  # Lamination
            self.nav_mag.setCurrentIndex(1)
