import os
import maya.cmds as cmds
import maya.OpenMaya as OpenMaya

global _old_positions
_old_positions = None


def get_alias_weight_dict(blendshape, reverse=False):
    """ get alias weight names as dict
        Args:
            :param str blendshape: name of blendshape node
            :param bool reverse: should weight dict be {weight_index: weight_alias_name} instead
        Return:
            :return dict weight_dict: {weight_alias_name : weight_index}
    """
    weight_dict = {}

    all_weight_alias = cmds.aliasAttr(blendshape, query=True)
    if not all_weight_alias:
        return weight_dict

    if reverse:
        for index in range(0, len(all_weight_alias), 2):
            weight_dict[int(all_weight_alias[index + 1].split("[")[-1].split("]")[0])] = all_weight_alias[index]

    else:
        for index in range(0, len(all_weight_alias), 2):
            weight_dict[all_weight_alias[index]] =  int(all_weight_alias[index + 1].split("[")[-1].split("]")[0])
    return weight_dict


def uncheckBlendshapeAttributes(blendshape_node):
    """ uncheck the blendshape custom edit attribut
        Args:
            :param str blendshape_node: name of the blendshape node
        Return:
            :return None
    """
    attribute_names = cmds.listAttr(blendshape_node, multi=True) or []

    for attribute_name in attribute_names:
        if attribute_name.startswith("index") and attribute_name.endswith("TargetEdit"):
            cmds.setAttr(blendshape_node + "." + attribute_name, 0)
    return None


def createCacheFolder(sel):
    """ create the cache folder based on the maya scene
        Args:
            :param str sel: selected
        Return:
            :return str newObjectName: incrementedNumber
    """
    sceneFolder = cmds.file(query=True, sceneName=True)
    sceneName = sceneFolder.split("/")[-1]
    sceneFolder = sceneFolder.replace(sceneName,"")
    cacheFolder = sceneFolder + "/cacheSculpt/"+sel

    if not os.path.exists(cacheFolder):
        os.makedirs(cacheFolder)

    return cacheFolder


def getAnimationCurve(objectName, attributeName):
    """get the targets based on the attribut

    Args:
        objectName (str): name of the mesh
        attributeName (str): name of the attribut

    Returns:
        animKey (list): list of the targets
    """
    if not cmds.objExists(objectName):
        return None

    if not cmds.attributeQuery(attributeName, node = objectName, exists = True):
        return None

    animKey = cmds.listConnections('{}.{}'.format(objectName, attributeName), plugs = True)
    animKey = animKey[0].replace(".output","")
    return animKey


def getVertexPositions(mesh):
    """get the position of the vertex

    Args:
        mesh (str): name of the mesh

    Returns:
        vertexPosList (list): pos x y z
    """
    vertex_count = cmds.polyEvaluate(mesh, vertex=True)
    vertexPosList = []
    for i in range(vertex_count):
        vertex_name = "{}.vtx[{}]".format(mesh, i)
        vertex_position = cmds.xform(vertex_name, query=True, translation=True, worldSpace=False)
        vertexPosList.append(vertex_position)
    return vertexPosList


def getDifVectorPos(vertex_pos1, vertex_pos2):
    """calculate pos bettween tow list of pos

    Args:
        vertex_pos1 (list): pos x y z
        vertex_pos2 (list): pos x y z

    Returns:
        vertex_diff (list): pos x y z
    """
    vertex_diff = [[pos2[0] - pos1[0], pos2[1] - pos1[1], pos2[2] - pos1[2]] for pos1, pos2 in zip(vertex_pos1, vertex_pos2)]
    return vertex_diff


def addPositionValueToVertices(vertex_list, position_values):
    """Add position values to the vertices in the specified list.

    Args:
        vertex_list (list): List of vertex names.
        position_values (list): List of position values.

    Returns:
        None
    """
    for i, vertex in enumerate(vertex_list):
        cmds.move(position_values[i][0], position_values[i][1], position_values[i][2], vertex, relative=True)
    return None




