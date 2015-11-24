import json, difflib
import os
import traceback

from PySide import QtGui, QtCore

from contextual_node_list import ContextualNodeList
from pyflowgraph.graph_view_widget import GraphViewWidget
from kgraph_view import KGraphView
from kraken.ui.undoredo.undo_redo_manager import UndoRedoManager
import graph_commands

from kraken.core.objects.rig import Rig
from kraken import plugins


def GetKrakenPath():
    if 'KRAKEN_PATH' in os.environ:
        return os.environ['KRAKEN_PATH']
    return os.path.expanduser("~")


class KGraphViewWidget(GraphViewWidget):

    rigNameChanged = QtCore.Signal()

    def __init__(self, parent=None):

        # constructors of base classes
        super(KGraphViewWidget, self).__init__(parent)


        graphView = KGraphView(parent=self)
        graphView.nodeAdded.connect(self.__onNodeAdded)
        graphView.nodeRemoved.connect(self.__onNodeRemoved)
        graphView.beginConnectionManipulation.connect(self.__onBeginConnectionManipulation)
        graphView.endConnectionManipulation.connect(self.__onEndConnectionManipulationSignal)
        graphView.connectionAdded.connect(self.__onConnectionAdded)
        graphView.connectionRemoved.connect(self.__onConnectionRemoved)

        graphView.selectionChanged.connect(self.__onSelectionChanged)
        graphView.endSelectionMoved.connect(self.__onSelectionMoved)

        graphView.beginDeleteSelection.connect(self.__onBeginDeleteSelection)
        graphView.endDeleteSelection.connect(self.__onEndDeleteSelection)

        self.setGraphView(graphView)

        #########################
        ## Setup hotkeys for the following actions.

        undoShortcut = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_Z), self)
        undoShortcut.activated.connect(self.undo)

        redoShortcut = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_Y), self)
        redoShortcut.activated.connect(self.redo)

        openContextualNodeListShortcut = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Tab), self)
        openContextualNodeListShortcut.activated.connect(self.openContextualNodeList)

        self.newRigPreset()


    def editRigName(self):
        dialog = QtGui.QInputDialog(self)
        dialog.setObjectName('RigNameDialog')
        text, ok = dialog.getText(self, 'Edit Rig Name', 'New Rig Name', text=self.guideRig.getName())

        if ok is True:
            self.setRigName(text)


    def setRigName(self, text):
        self.guideRig.setName(text)
        self.rigNameChanged.emit()


    def newRigPreset(self):
        self.guideRig = Rig()
        self.getGraphView().displayGraph(self.guideRig)
        self.setRigName('MyRig')

        self.openedFile = None

        self.window().setWindowTitle('Kraken Editor')


    def saveRig(self, saveAs=False):
        """Saves the current rig to disc.

        Args:
            saveAs (Boolean): Determines if this was a save as call or just a normal save.

        Returns:
            String: Path to the saved file.

        """


        settings = self.window().getSettings()
        settings.beginGroup('Files')
        filePath = settings.value("lastFilePath", os.path.join(GetKrakenPath(), self.guideRig.getName() ))
        settings.endGroup()

        if saveAs is True:

            (saveAsFilePath, filter) = QtGui.QFileDialog.getSaveFileName(self, 'Save Rig Preset', os.path.dirname(os.path.abspath(filePath)), 'Kraken Rig (*.krg)', options=QtGui.QFileDialog.DontUseNativeDialog)
            if len(saveAsFilePath) > 0:
                filePath = saveAsFilePath
            else:
                return False

        self.synchGuideRig()
        self.guideRig.writeRigDefinitionFile(filePath)

        settings.beginGroup('Files')
        lastFilePath = settings.setValue("lastFilePath", filePath)
        settings.endGroup()

        self.openedFile = filePath

        self.reportMessage('Saved Rig file: ' + filePath, level='information')

        return filePath


    def saveAsRigPreset(self):
        """Opens a dialogue window to save the current rig as a different file."""

        filePath = self.saveRig(saveAs=True)
        if filePath is not False:
            self.window().setWindowTitle('Kraken Editor - ' + filePath + '[*]')


    def saveRigPreset(self):

        if self.openedFile is None or not os.path.exists(self.openedFile):
            self.saveRig(saveAs=True)

        else:
            self.saveRig(saveAs=False)


    def loadRigPreset(self):
        settings = self.window().getSettings()
        settings.beginGroup('Files')
        lastFilePath = settings.value("lastFilePath", os.path.join(GetKrakenPath(), self.guideRig.getName() ))
        settings.endGroup()
        (filePath, filter) = QtGui.QFileDialog.getOpenFileName(self, 'Load Rig Preset', os.path.dirname(os.path.abspath(lastFilePath)), 'Kraken Rig (*.krg)', options=QtGui.QFileDialog.DontUseNativeDialog)
        if len(filePath) > 0:
            self.guideRig = Rig()
            self.guideRig.loadRigDefinitionFile(filePath)
            self.graphView.displayGraph( self.guideRig )
            # self.nameWidget.setText( self.guideRig.getName() )

            settings.beginGroup('Files')
            lastFilePath = settings.setValue("lastFilePath", filePath)
            settings.endGroup()

            self.openedFile = filePath

            self.window().setWindowTitle('Kraken Editor - ' + filePath + '[*]')

            self.reportMessage('Loaded Rig file: ' + filePath, level='information')


    def buildGuideRig(self):

        try:
            self.window().statusBar().showMessage('Building Guide')

            builder = plugins.getBuilder()

            if self.guideRig.getName().endswith('_guide') is False:
                self.guideRig.setName(self.guideRig.getName() + '_guide')

            builder.build(self.guideRig)

        except Exception as e:
            self.reportMessage('Error Building', level='error', exception=e)


    def synchGuideRig(self):
        synchronizer = plugins.getSynchronizer()
        synchronizer.setTarget(self.guideRig)
        synchronizer.sync()


    def buildRig(self):

        try:
            self.window().statusBar().showMessage('Building Rig')

            self.synchGuideRig()

            rigBuildData = self.guideRig.getRigBuildData()
            rig = Rig()
            rig.loadRigDefinition(rigBuildData)

            rig.setName(rig.getName().replace('_guide', ''))

            builder = plugins.getBuilder()
            builder.build(rig)

        except Exception as e:
            self.reportMessage('Error Building', level='error', exception=e)

    # =========
    # Shortcuts
    # =========
    def copy(self):
        graphView = self.getGraphView()
        pos = graphView.getSelectedNodesCentroid()
        graphView.copySettings(pos)


    def paste(self):
        graphView = self.getGraphView()
        clipboardData = self.graphView.getClipboardData()

        pos = clipboardData['copyPos'] + QtCore.QPoint(20, 20)
        graphView.pasteSettings(pos, mirrored=False, createConnectionsToExistingNodes=True)


    def pasteUnconnected(self):
        graphView = self.getGraphView()
        clipboardData = self.graphView.getClipboardData()

        pos = clipboardData['copyPos'] + QtCore.QPoint(20, 20)
        graphView.pasteSettings(pos, mirrored=False, createConnectionsToExistingNodes=False)


    def pasteMirrored(self):
        graphView = self.getGraphView()
        clipboardData = self.graphView.getClipboardData()

        pos = clipboardData['copyPos'] + QtCore.QPoint(20, 20)
        graphView.pasteSettings(pos, mirrored=True, createConnectionsToExistingNodes=False)


    def pasteMirroredConnected(self):
        graphView = self.getGraphView()
        clipboardData = self.graphView.getClipboardData()

        pos = clipboardData['copyPos'] + QtCore.QPoint(20, 20)
        graphView.pasteSettings(pos, mirrored=True, createConnectionsToExistingNodes=True)


    def undo(self):
        UndoRedoManager.getInstance().undo()

    def redo(self):
        UndoRedoManager.getInstance().redo()


    def openContextualNodeList(self):
        pos = self.mapFromGlobal(QtGui.QCursor.pos());

        contextualNodeList = ContextualNodeList(self)

        scenepos = self.graphView.mapToScene(pos)
        contextualNodeList.showAtPos(pos, scenepos, self.graphView)


    # ==================
    # Message Reporting
    # ==================
    def reportMessage(self, message, level='error', exception=None):
        """Shows an error message in the status bar.

        Args:
            message (str): Message to display to the user.

        """

        statusBar = self.window().statusBar()

        if exception is not None:
            fullMessage = level[0].upper() + level[1:] + ": " + message + '; ' + ', '.join([x for x in exception.args])
        else:
            fullMessage = level[0].upper() + level[1:] + ": " + message

        messageLabel = QtGui.QLabel(fullMessage)

        print fullMessage

        messageColors = {
            'information': '#009900',
            'warning': '#CC3300',
            'error': '#AA0000'
        }

        if level not in messageColors.keys():
            level = 'error'

        messageLabel.setStyleSheet("QLabel { border-radius: 3px; background-color: " + messageColors[level] + "}")

        def addMessage():
            self.window().statusBar().clearMessage()

            statusBar.addWidget(messageLabel, 1)
            statusBar.repaint()

            timer.start()

        def endMessage():
            timer.stop()
            statusBar.removeWidget(messageLabel)
            statusBar.repaint()

            self.window().statusBar().showMessage('Ready', 2000)

        timer = QtCore.QTimer()
        timer.setInterval(3500)
        timer.timeout.connect(endMessage)

        addMessage()


    # ===============
    # Signal Handlers
    # ===============
    def __onNodeAdded(self, node):
        if not UndoRedoManager.getInstance().isUndoingOrRedoing():
            command = graph_commands.AddNodeCommand(self.graphView, self.guideRig, node)
            UndoRedoManager.getInstance().addCommand(command)


    def __onNodeRemoved(self, node):
        node.getComponent().detach()

        if not UndoRedoManager.getInstance().isUndoingOrRedoing():
            command = graph_commands.RemoveNodeCommand(self.graphView, self.guideRig, node)
            UndoRedoManager.getInstance().addCommand(command)


    def __onBeginConnectionManipulation(self):
        UndoRedoManager.getInstance().openBracket('Connect Ports')


    def __onEndConnectionManipulationSignal(self):
        UndoRedoManager.getInstance().closeBracket()


    def __onConnectionAdded(self, connection):
        if not UndoRedoManager.getInstance().isUndoingOrRedoing():
            command = graph_commands.ConnectionAddedCommand(self.graphView, self.guideRig, connection)
            UndoRedoManager.getInstance().addCommand(command)


    def __onConnectionRemoved(self, connection):
        if not UndoRedoManager.getInstance().isUndoingOrRedoing():
            command = graph_commands.ConnectionRemovedCommand(self.graphView, self.guideRig, connection)
            UndoRedoManager.getInstance().addCommand(command)


    def __onSelectionChanged(self, deselectedNodes, selectedNodes):
        if not UndoRedoManager.getInstance().isUndoingOrRedoing():
            command = graph_commands.SelectionChangeCommand(self.graphView, deselectedNodes, selectedNodes)
            UndoRedoManager.getInstance().addCommand(command)


    def __onSelectionMoved(self, nodes, delta):
        if not UndoRedoManager.getInstance().isUndoingOrRedoing():
            command = graph_commands.NodesMoveCommand(self.graphView, nodes, delta)
            UndoRedoManager.getInstance().addCommand(command)


    def __onBeginDeleteSelection(self):
        UndoRedoManager.getInstance().openBracket('Delete Nodes')


    def __onEndDeleteSelection(self):
        UndoRedoManager.getInstance().closeBracket()