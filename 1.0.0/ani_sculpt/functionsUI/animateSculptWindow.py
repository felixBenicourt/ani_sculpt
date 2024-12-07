import maya.cmds as cmds
import maya.OpenMayaUI as omui
from PySide2 import QtWidgets, QtCore, QtGui
import maya.mel as mel
import shiboken2
import CONSTANTS
import functionsCore.coreProcs
import functionsCore.coreCmds
reload(functionsCore.coreProcs)
reload(functionsCore.coreCmds)


def getMayaMainWindow():
    ptr = omui.MQtUtil.mainWindow()
    return shiboken2.wrapInstance(int(ptr), QtWidgets.QMainWindow)

class MayaEventFilter(QtCore.QObject):
    selectionChanged = QtCore.Signal(list)

    def __init__(self, parent=None):
        super(MayaEventFilter, self).__init__(parent)
        self.scriptJobID = None

    def startMonitoring(self):
        self.scriptJobID = cmds.scriptJob(event=["SelectionChanged", self.onSelectionChanged])

    def stopMonitoring(self):
        try:
            if self.scriptJobID is not None:
                cmds.scriptJob(kill=self.scriptJobID, force=True)
                self.scriptJobID = None
        except:
            pass

    def onSelectionChanged(self):
        selectedMeshes = cmds.ls(selection=True, long=True, dag=True, shapes=True)
        self.selectionChanged.emit(selectedMeshes)


class BlendshapeItemDelegate(QtWidgets.QStyledItemDelegate):

    def __init__(self, parent=None):
        super(BlendshapeItemDelegate, self).__init__(parent)

    def sizeHint(self, option, index):
        height = 32
        width = option.rect.width()
        return QtCore.QSize(width, height)

    def paint(self, painter, option, index):
        option.textElideMode = QtCore.Qt.ElideRight
        background_color = QtGui.QColor(80, 80, 80)
        text_color = QtGui.QColor(255, 255, 255)

        if option.state & QtWidgets.QStyle.State_Selected:
            background_color = QtGui.QColor(0, 160, 200)

        painter.fillRect(option.rect, background_color)
        painter.setPen(text_color)
        painter.drawText(option.rect, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, index.data())


class RoundCheckBoxStyle(QtWidgets.QProxyStyle):

    def drawPrimitive(self, element, option, painter, widget=None):
        if element == QtWidgets.QStyle.PE_IndicatorCheckBox:
            check_box_rect = self.subElementRect(QtWidgets.QStyle.SE_CheckBoxIndicator, option, widget)

            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(option.palette.mid())
            painter.drawEllipse(check_box_rect)

            if option.state & QtWidgets.QStyle.State_On:
                checkmark_rect = QtCore.QRectF(check_box_rect)
                checkmark_rect.adjust(4, 4, -4, -4)
                painter.setBrush(QtGui.QColor(255, 0, 0))
                painter.drawEllipse(checkmark_rect)

            return

        super().drawPrimitive(element, option, painter, widget)


class NodeWidget(QtWidgets.QWidget):
    selectionChanged = QtCore.Signal(list)
    layerRenamed = QtCore.Signal(str, str)
    layerAdded = QtCore.Signal(str)
    layerRemoved = QtCore.Signal(str)

    def __init__(self, parent=None):
        super(NodeWidget, self).__init__(parent)

        self.eventFilter = MayaEventFilter(self)
        self.sliderWidgets = {}
        layout = QtWidgets.QVBoxLayout()

        self.layersListWidget = QtWidgets.QListWidget(self)
        self.layersListWidget.setItemDelegate(BlendshapeItemDelegate(self))
        self.layersListWidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.layersListWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.layersListWidget.customContextMenuRequested.connect(self.showContextMenu)
        layout.addWidget(self.layersListWidget)

        recordLayout = QtWidgets.QHBoxLayout()

        self.selectedLayerLabel = QtWidgets.QLabel()
        self.selectedLayerLabel.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.selectedLayerLabel)

        self.recordCheckBox = QtWidgets.QCheckBox("Record mesh target")
        self.recordCheckBox.setObjectName("recordCheckBox")
        self.recordCheckBox.setChecked(False)
        self.recordCheckBox.setStyle(RoundCheckBoxStyle())
        record_checkbox_style = "QCheckBox#recordCheckBox { padding-right: 5px; }"
        self.recordCheckBox.setStyleSheet(record_checkbox_style)
        self.recordCheckBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        recordLayout.addWidget(self.recordCheckBox)

        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        recordLayout.addItem(spacerItem)

        buttonLayout = QtWidgets.QHBoxLayout()

        self.editLayerButton = QtWidgets.QPushButton()
        self.editLayerButton.setFixedWidth(30)
        self.editLayerButton.setFixedHeight(30)
        icon = QtGui.QIcon(CONSTANTS.editIcon)
        self.editLayerButton.setIcon(icon)
        self.editLayerButton.clicked.connect(self.editTargetShape)
        buttonLayout.addWidget(self.editLayerButton)

        self.addLayerButton = QtWidgets.QPushButton()
        self.addLayerButton.setFixedWidth(30)
        self.addLayerButton.setFixedHeight(30)
        icon = QtGui.QIcon(CONSTANTS.targetIcon)
        self.addLayerButton.setIcon(icon)
        self.addLayerButton.clicked.connect(self.addLayer)
        buttonLayout.addWidget(self.addLayerButton)

        self.openGraphEditorButton = QtWidgets.QPushButton()
        self.openGraphEditorButton.setFixedWidth(30)
        self.openGraphEditorButton.setFixedHeight(30)
        icon = QtGui.QIcon(CONSTANTS.graphIcon)
        self.openGraphEditorButton.setIcon(icon)
        self.openGraphEditorButton.clicked.connect(self.openGraphEditor)
        buttonLayout.addWidget(self.openGraphEditorButton)

        recordLayout.addLayout(buttonLayout)

        layout.addLayout(recordLayout)

        blendshapeText = QtWidgets.QLabel("Blendshape Weight :")
        layout.addWidget(blendshapeText) 

        self.sliderGroup = QtWidgets.QGroupBox()
        self.sliderLayout = QtWidgets.QVBoxLayout()
        self.sliderGroup.setLayout(self.sliderLayout)
        self.sliderGroup.setStyleSheet("QGroupBox { border: 1px solid gray; border-radius: 3px; background-color: #424242; }")
        self.sliderGroup.setMinimumHeight(50)
        layout.addWidget(self.sliderGroup)

        spacerItem2 = QtWidgets.QSpacerItem(0, 14)
        layout.addItem(spacerItem2)

        self.saveLayersButton = QtWidgets.QPushButton("Save Layers")
        self.saveLayersButton.clicked.connect(self.saveLayers)
        layout.addWidget(self.saveLayersButton)

        self.loadLayersButton = QtWidgets.QPushButton("Load Layers")
        self.loadLayersButton.clicked.connect(self.loadLayers)
        layout.addWidget(self.loadLayersButton)

        spacerItem3 = QtWidgets.QSpacerItem(0, 26)
        layout.addItem(spacerItem3)

        self.setLayout(layout)
        self.layersListWidget.itemSelectionChanged.connect(self.handleLayerSelectionChanged)


    def editTargetShape(self):
        selectedItems = self.layersListWidget.selectedItems()
        selection = cmds.ls(sl=True)
        for node in cmds.listHistory(selection[0]):
            if cmds.nodeType(node) == "blendShape":
                blendshape_node = node
        if selectedItems:
            selectedLayer = selectedItems[0].text()
            self.selectedLayerLabel.setText(selectedLayer)
            functionsCore.coreProcs.editSelectedTarget(blendshape_node, selectedLayer)


    def showContextMenu(self, pos):
        menu = QtWidgets.QMenu(self)
        delete_layer_action = menu.addAction("Delete Layer")
        action = menu.exec_(self.layersListWidget.viewport().mapToGlobal(pos))
        if action == delete_layer_action:
            selected_items = self.layersListWidget.selectedItems()
            if selected_items:
                for item in selected_items:
                    self.deleteSelectedLayers(item)


    def saveLayers(self):
        selection = cmds.ls(sl=True)
        for node in cmds.listHistory(selection[0]):
            if cmds.nodeType(node) == "blendShape":
                blendshape_node = node
                functionsCore.coreProcs.saveAnimation(blendshape_node)


    def loadLayers(self):
        selectedMeshes = cmds.ls(selection=True)
        if selectedMeshes:
            for mesh in selectedMeshes:
                    mesh = "{}_postAnim".format(mesh)
                    functionsCore.coreProcs.loadAnimation(mesh)


    def openGraphEditor(self):
        mel.eval('GraphEditor')


    def isRecordCheckBoxChecked(self):
            return self.recordCheckBox.isChecked()


    def handleLayerSelectionChanged(self):
        selectedItems = self.layersListWidget.selectedItems()
        if selectedItems:
            selectedLayer = selectedItems[0].text()
            self.createSliderWidget(selectedLayer)


    def clearSliderWidgets(self):
        for widget in self.sliderWidgets.values():
            self.sliderLayout.removeWidget(widget)
            widget.deleteLater()
        self.sliderWidgets.clear()


    def updateBlendshapeSelection(self, selectedMeshes):
        self.layersListWidget.clear()
        self.clearSliderWidgets()
        selection = cmds.ls(sl=True)
        if cmds.nodeType(selection[0]) == "transform":
            for obj in selection:
                for node in cmds.listHistory(obj):
                    if cmds.nodeType(node) == "blendShape":
                        for target in cmds.listAttr("{}.weight".format(node), multi=True):
                            self.layersListWidget.addItem(target)


    def setSliderValue(self, blendshape_node):
        slider = self.sliderWidgets.get(blendshape_node)
        if slider is not None:
            weight = cmds.getAttr(blendshape_node + ".w[0]") * 100.0
            slider.setSliderPosition(int(weight))


    def frameChangedCallback(self):
        selectedItems = self.layersListWidget.selectedItems()
        if selectedItems:
            selectedLayer = selectedItems[0].text()
            selection = cmds.ls(sl=True)
            if cmds.nodeType(selection[0]) == "transform":
                for obj in selection:
                    for node in cmds.listHistory(obj):
                        if cmds.nodeType(node) == "blendShape":
                            blendShape = node
                weight = cmds.getAttr("{}.{}".format(blendShape, selectedLayer)) * 100.0
                slider = self.sliderWidgets.get(blendShape)
                if slider is not None:
                    slider.setValue(int(weight))


    def onSliderValueChanged(self, blendshape_node, value):
        weight = value / 100.0
        selectedLayer = self.layersListWidget.selectedItems()
        selectedLayer = selectedLayer[0].text()
        cmds.setAttr("{}.{}".format(blendshape_node, selectedLayer), weight)
        mel.eval('setKeyframe "{}.{}";'.format(blendshape_node,selectedLayer))


    def deleteSelectedLayers(self, item):
        selection = cmds.ls(sl=True)
        for node in cmds.listHistory(selection[0]):
            if cmds.nodeType(node) == "blendShape":
                blendshape_node = node
        indexDict = functionsCore.coreCmds.get_alias_weight_dict(blendshape_node)
        selected_index = indexDict[item.text()]
        functionsCore.coreProcs.delete_blendshape_target(blendshape_node, selected_index)
        self.layersListWidget.takeItem(self.layersListWidget.row(item))
        self.layerRemoved.emit(item.text())


    def createSliderWidget(self, selectedLayer):
        selection = cmds.ls(sl=True)
        for node in cmds.listHistory(selection[0]):
            if cmds.nodeType(node) == "blendShape":
                blendshape_node = node
        selectedItems = self.layersListWidget.selectedItems()
        if selectedItems:
            weight_attr = "{}.{}".format(blendshape_node, selectedLayer)
            weight = cmds.getAttr(weight_attr) * 100.0
            if blendshape_node in self.sliderWidgets:
                slider = self.sliderWidgets[blendshape_node]
                slider.setSliderPosition(int(weight))
            else:
                slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
                slider.setMinimum(0)
                slider.setMaximum(100)
                slider.setSliderPosition(int(weight))
                slider.valueChanged.connect(lambda value, bs_node=blendshape_node: self.onSliderValueChanged(bs_node, value))
                slider.setObjectName(blendshape_node)
                self.sliderWidgets[blendshape_node] = slider
                self.sliderLayout.addWidget(slider)


    def removeSliderWidget(self, blendshape_node):
        if blendshape_node in self.sliderWidgets:
            slider = self.sliderWidgets[blendshape_node]
            slider.deleteLater()
            del self.sliderWidgets[blendshape_node]


    def addLayer(self):
        selectedMeshes = cmds.ls(selection=True)
        selectedItems = self.layersListWidget.selectedItems()
        if selectedItems:
            selectedLayer = selectedItems[0].text()
        if selectedMeshes:
            for mesh in selectedMeshes:
                isRecording = self.isRecordCheckBoxChecked()
                if isRecording:
                    mesh = "{}_postAnim".format(mesh)
                    blendshape_node = functionsCore.coreProcs.createBlendshapeWithTarget(mesh)
                    selectedItems = self.layersListWidget.selectedItems()
                    if selectedItems:
                        mel.eval('setAttr "{}.{}";'.format(blendshape_node,selectedLayer), 1.0)


def showLayerEditor():
    mainWindow = getMayaMainWindow()
    mainWindow.findChildren(QtWidgets.QDockWidget, "Ani-Sculpt")
    blendshapeEditor = NodeWidget(parent=mainWindow)
    cmds.scriptJob(event=["timeChanged", blendshapeEditor.frameChangedCallback])
    dockWidget = QtWidgets.QDockWidget("Ani-Sculpt", mainWindow)
    dockWidget.setObjectName("Ani-Sculpt")
    dockWidget.setWidget(blendshapeEditor)
    mainWindow.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dockWidget)
    eventFilter = blendshapeEditor.eventFilter
    eventFilter.startMonitoring()
    eventFilter.selectionChanged.connect(blendshapeEditor.updateBlendshapeSelection)
    dockWidget.show()


