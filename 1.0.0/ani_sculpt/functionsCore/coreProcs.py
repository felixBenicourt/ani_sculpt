
import maya.cmds as cmds
import maya.mel as mel
import re
import json
import os

import functionsCore.coreCmds
reload(functionsCore.coreCmds)


def delete_blendshape_target(blendshape_name, targetName):
    """ delete target of the blendshape
        Args:
            :param str blendshape_name: name of blendshape node
            :param int target_index: index of the target
        Return:
            None
    """
    dictTarget = functionsCore.coreCmds.get_alias_weight_dict(blendshape_name)
    targetIdx = 0
    if dictTarget:
        targetIdx = targetIdx+1
    mel.eval('blendShapeDeleteTargetGroup {} {};'.format(blendshape_name, targetName))
    return None


def editSelectedTarget(blendshape_node, selectedLayer):
    """ put the mesh at the created key frame and put the target in edit mode 
        Args:
            :param str blendshape_node: name of blendshape node
            :param str selectedLayer: name of selected layer
        Return:
            None
    """
    dictTarget = functionsCore.coreCmds.get_alias_weight_dict(blendshape_node)
    selectedLayerList = selectedLayer.split("_")

    pattern = r"^f\d+$"
    frame = [element for element in selectedLayerList if re.match(pattern, element)]
    frame = float(frame[0].replace("f",""))
    cmds.currentTime(frame)

    dictTarget = functionsCore.coreCmds.get_alias_weight_dict(blendshape_node)
    target_index = dictTarget[selectedLayer]

    if not cmds.getAttr("{}.index{}TargetEdit".format(blendshape_node, target_index)):
        cmds.warning("{}.index{}TargetEdit".format(blendshape_node, target_index))
        mel.eval('sculptTarget -e -target {} {};'.format(target_index, blendshape_node))
        functionsCore.coreCmds.uncheckBlendshapeAttributes(blendshape_node)
        mel.eval('setAttr "{}.index{}TargetEdit" 1;'.format(blendshape_node, target_index))
    return "{}.index{}TargetEdit".format(blendshape_node, target_index)


def createBlendshapeWithTarget(blendshape_name):
    """ create a blendshape node with the first target and add new target in edit mode when the blendshape node is already existing
        Args:
            :param str blendshape_name: name of blendshape node
        Return:
            None
    """
    selection = cmds.ls(selection=True)
    if not selection:
        cmds.warning("Please select the base object for the blendShape.")
        return

    base_object = selection[0]

    if cmds.objExists(blendshape_name) and cmds.listAttr("{}.weight".format(blendshape_name), multi=True) is None:
        cmds.delete(blendshape_name)

    if not cmds.objExists(blendshape_name):
        blendshape_node = cmds.blendShape(base_object, name=blendshape_name)
        blendshape_node = blendshape_node[0]
    else:
        blendshape_node = blendshape_name

    cmds.setAttr("{}.envelope".format(blendshape_node), 0)

    currentFrame = cmds.currentTime(query=True)
    target_name = "{}_f{}_target_0".format(blendshape_node, int(currentFrame))
    dictTarget = functionsCore.coreCmds.get_alias_weight_dict(blendshape_name)

    if not dictTarget:
        target_index = 0
    else:
        target_index = max(dictTarget.values())

    target_index = target_index+1
    target_object = cmds.duplicate(base_object, name=target_name.split(':')[-1])[0]

    cmds.blendShape(blendshape_node, edit=True, target=(base_object, target_index, target_object, 1.0))

    all_weight_alias = cmds.aliasAttr(blendshape_node, query=True)
    mel.eval('setAttr "{}.{}" {};'.format(blendshape_node,all_weight_alias[-2],1.0))
    mel.eval('sculptTarget -e -target {} {};'.format(target_index, blendshape_node))
    mel.eval('setKeyframe "{}.w[{}]";'.format(blendshape_node, target_index))
    mel.eval('addAttr -ln "index{}TargetEdit" -at bool {};'.format(target_index,blendshape_node))

    functionsCore.coreCmds.uncheckBlendshapeAttributes(blendshape_node)

    mel.eval('setAttr "{}.index{}TargetEdit" 1;'.format(blendshape_node, target_index))
    mel.eval('addAttr -ln"index{}TargetFrame" -at double -dv {} {};'.format(target_index, currentFrame, blendshape_node))
    
    cmds.delete(target_object)
    cmds.select(selection)
    cmds.setAttr("{}.envelope".format(blendshape_node), 1)
    return None


def renameTarget(current_name, new_name):
    """ rename the target of the blendshape
        Args:
            :param str current_name: current target you want to rename
            :param str new_name: new name the the current target
        Return:
            None
    """
    selectedMeshes = cmds.ls(selection=True)
    myHistory = cmds.listHistory(selectedMeshes)
    myBlendShapeNodes = cmds.ls(myHistory, type='blendShape')
    for blendShapeNode in myBlendShapeNodes:
        if cmds.attributeQuery(current_name, node=blendShapeNode, exists=True):
            cmds.aliasAttr(new_name, '{}.{}'.format(blendShapeNode, current_name))
            break
    cmds.select(selectedMeshes)
    return None


def getBlendshapeAnimationData(blendshape):
    """ save the blendshapes targets of the mesh with their key animations
        Args:
            :param str blendshape: blendshape node
        Return:
            None
    """
    selectedMeshes = cmds.ls(selection=True)
    targets = functionsCore.coreCmds.get_alias_weight_dict(blendshape)
    targets = targets.keys()
    animationData = {}

    for target in targets:
        for targ in targets:
            cmds.setAttr("{}.{}".format(blendshape, targ),0)
    
        cmds.setAttr("{}.{}".format(blendshape, target),1)
        meshPosTarget = functionsCore.coreCmds.getVertexPositions(selectedMeshes[0])
        cmds.setAttr("{}.{}".format(blendshape, target),0)
        meshPosOrigin = functionsCore.coreCmds.getVertexPositions(selectedMeshes[0])
        keyName = functionsCore.coreCmds.getAnimationCurve(blendshape, target)
        cmds.warning(keyName)
        vectorDiff = functionsCore.coreCmds.getDifVectorPos(meshPosOrigin, meshPosTarget)
        match = re.search(r"_f(\d+)_", target)

        if not match:
            continue
        frame = int(match.group(1))

        animationData[keyName] = {'originFrame':frame, 'keyNode':keyName, 'positionsValues':vectorDiff}
    return animationData


def load_data_from_json(file_path):
    """Load data from a JSON file.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        dict: Loaded data.
    """
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data


def saveAnimation(blendshape):
    """Load data from a JSON file.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        dict: Loaded data.
    """
    animationData = getBlendshapeAnimationData(blendshape)
    scene_path = cmds.file(query=True, sceneName=True)
    scene_directory = os.path.dirname(scene_path)
    scene_name = os.path.splitext(os.path.basename(scene_path))[0]
    json_file_path = "{}/{}_animation_data.json".format(scene_directory, scene_name)

    with open(json_file_path, 'w') as file:
        json.dump(animationData, file, indent=4)

    cmds.warning('Animation data saved: {}'.format(json_file_path))
    return None


def loadAnimation(blendshape):
    """Load data from a JSON file.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        dict: Loaded data.
    """
    selectedMeshes = cmds.ls(selection=True)
    scene_path = cmds.file(query=True, sceneName=True)
    scene_directory = os.path.dirname(scene_path)
    scene_name = os.path.splitext(os.path.basename(scene_path))[0]
    json_file_path = "{}/{}_animation_data.json".format(scene_directory,scene_name)
    loaded_data = load_data_from_json(json_file_path)

    for key, value in loaded_data.items():
        dictTarget = functionsCore.coreCmds.get_alias_weight_dict(blendshape)
        print(dictTarget)

        if not dictTarget:
            target_index = 0
        else:
            target_index = max(dictTarget.values())

        if not cmds.objExists(blendshape):
            blendshape_node = cmds.blendShape(selectedMeshes[0], name=blendshape)
            blendshape_node = blendshape_node[0]
        else:
            blendshape_node = blendshape
        target_index = target_index+1
        target_object = cmds.duplicate(selectedMeshes[0], name=key)[0]
        vertexesList = cmds.ls(target_object+".vtx[*]", flatten=True)
        functionsCore.coreCmds.addPositionValueToVertices(vertexesList, value['positionsValues'])
        print(target_index)
        cmds.blendShape(blendshape_node, edit=True, target=(selectedMeshes[0], target_index,target_object, 1.0))
        cmds.duplicate(value['keyNode'], rr=True, n="{}_postAnim_f{}_target_0".format(selectedMeshes[0], value['originFrame']))
        cmds.connectAttr("{}.output".format(key, value['originFrame']),"{}.{}".format(blendshape, target_object), f=True)
        cmds.delete(target_object)
        cmds.select(selectedMeshes)
    return None

