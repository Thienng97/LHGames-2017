from flask import Flask, request
from structs import *
import json
import numpy

app = Flask(__name__)

shopPosition = -1
prevMove = {0, 0}
doubleMove = False
invalidPos = []

capacitylvl = 0;
speedlvl = 0;

def create_action(action_type, target):
    actionContent = ActionContent(action_type, target.__dict__)
    return json.dumps(actionContent.__dict__)


def create_move_action(target):
    return create_action("MoveAction", target)

def create_attack_action(target):
    return create_action("AttackAction", target)

def create_collect_action(target):
    return create_action("CollectAction", target)

def create_steal_action(target):
    return create_action("StealAction", target)

def create_heal_action():
    return create_action("HealAction", "")

def create_purchase_action(item):
    return create_action("PurchaseAction", item)

def create_upgrade_action(upgrade):
    return json.dumps({"ActionName":"UpgradeAction","Content":upgrade})

def deserialize_map(serialized_map):
    """
    Fonction uti    litaire pour comprendre la map
    """
    serialized_map = serialized_map[1:]
    rows = serialized_map.split('[')
    column = rows[0].split('{')
    deserialized_map = [[Tile() for x in range(20)] for y in range(20)]
    for i in range(len(rows) - 1):
        column = rows[i + 1].split('{')

        for j in range(len(column) - 1):
            infos = column[j + 1].split(',')
            end_index = infos[2].find('}')
            content = int(infos[0])
            x = int(infos[1])
            y = int(infos[2][:end_index])
            deserialized_map[i][j] = Tile(content, x, y)

    return deserialized_map

def bot():
    global capacitylvl
    global speedlvl

    """
    Main de votre bot.
    """
    map_json = request.form["map"]

    # Player info

    encoded_map = map_json.encode()
    map_json = json.loads(encoded_map)
    p = map_json["Player"]
    print "player:{}".format(p)
    pos = p["Position"]
    x = pos["X"]
    y = pos["Y"]
    house = p["HouseLocation"]
    player = Player(p["Health"], p["MaxHealth"], Point(x,y),
                    Point(house["X"], house["Y"]),p["Score"],
                    p["CarriedResources"], p["CarryingCapacity"])

    # Map
    serialized_map = map_json["CustomSerializedMap"]
    deserialized_map = deserialize_map(serialized_map)

    otherPlayers = []

    for players in map_json["OtherPlayers"]:
        player_info = players["Value"]
        p_pos = player_info["Position"]
        player_info = PlayerInfo(player_info["Health"],
                                     player_info["MaxHealth"],
                                     Point(p_pos["X"], p_pos["Y"]))
        otherPlayers.append(player_info)


    if player.CarriedRessources == player.CarryingCapacity:
        homePos = goToPosition(player.HouseLocation, Point(x,y), deserialized_map)
        nextPos = goToPosition(homePos, Point(x,y), deserialized_map)

        if math.sqrt(pow(homePos.X - nextPos.X, 2) + pow(homePos.Y - nextPos.Y, 2)) <= 1:
            action = create_move_action(homePos)
        else:
            action = create_move_action(nextPos)
    elif p["TotalResources"] >= 15000 and capacitylvl == 0:
        action = create_upgrade_action(UpgradeType().CarryingCapacity)
        capacitylvl += 1
    elif p["TotalResources"] >= 15000 and speedlvl == 0:
        action = create_upgrade_action(UpgradeType().CollectingSpeed)
        speedlvl += 1
    else:
        resPos = findNearestResource(deserialized_map, x, y)
        nextPos = goToPosition(resPos, Point(x,y), deserialized_map)

        if math.sqrt(pow(resPos.X - nextPos.X, 2) + pow(resPos.Y - nextPos.Y, 2)) <= 1:
            action = create_collect_action(resPos)
        else:
            action = create_move_action(nextPos)

    # return decision
    return action


def findNearestResource(dmap, x, y):
    global shopPosition
    minDist = 20
    resPos = -1

    for  i in range(0,20):
        for j in range(0,20):
            if dmap[i][j].Content == TileContent().Resource:
                dist = math.sqrt(pow(dmap[i][j].X - x, 2) + pow(dmap[i][j].Y - y, 2))
                if dist < minDist:
                    minDist = dist
                    resPos = Point(dmap[i][j].X, dmap[i][j].Y)
            elif dmap[i][j].Content == TileContent().Shop:
                shopPosition = Point(dmap[i][j].X, dmap[i][j].Y)

    return resPos

def goToPosition(dest, current, dmap):
    global prevMove
    global doubleMove
    global invalidPos
    dx = dest.X - current.X
    dy = dest.Y - current.Y
    destPos = Point(current.X,current.Y)

    validPos = checkEnvironnement(findInMap(current.X,current.Y, dmap), dmap)

    if doubleMove:
        destPos = Point(current.X + prevMove[0],current.Y + prevMove[1])
        invalidPos.append((current.X - prevMove[0],current.Y - prevMove[1]))
        doubleMove = False
    else:
        if len(validPos) <= 1:
            doubleMove = True
        if dx > 0 and (current.X + 1, current.Y) in validPos:
            destPos = Point(current.X + 1, current.Y)
            prevMove = {1,0}
            #check if can move right
        elif dx < 0 and (current.X - 1, current.Y) in validPos:
            destPos = Point(current.X - 1, current.Y)
            prevMove = {-1,0}
            #check if can move left
        elif dy > 0 and (current.X, current.Y + 1) in validPos:
            destPos = Point(current.X, current.Y + 1)
            prevMove = {0,1}
            #check if can move up
        elif dy < 0  and (current.X, current.Y - 1) in validPos:
            destPos = Point(current.X, current.Y - 1)
            prevMove = {0,-1}
            #check if can move down
        elif (current.X + 1, current.Y) in validPos:
            destPos = Point(current.X + 1, current.Y)
            prevMove = {1,0}
        elif (current.X - 1, current.Y) in validPos:
            destPos = Point(current.X - 1, current.Y)
            prevMove = {-1,0}
        else:
            destPos = Point(current.X + prevMove[0], current.Y + prevMove[1])
            invalidPos.append((current.X - prevMove[0], current.Y - prevMove[1]))

    return destPos

def findInMap(x,y,dmap):
    for i in range(0,20):
        for j in range(0,20):
            if dmap[i][j].X == x and dmap[i][j].Y == y:
                return Point(i,j)

# checker si la capacite est full
def checkMaxCapacity(player):
    if player.CarriedRessources >= player.CarryingCapacity:
        return True
    elif player.CarriedRessources <= player.CarryingCapacity:
        return False

def checkEnvironnement(player, dmap):
    possiblePosition = []

    goodTile = [TileContent().Empty, TileContent().House]

    if dmap[player.Y][player.X - 1].Content in goodTile and (player.X-1,player.Y) not in invalidPos:
        possiblePosition.append((dmap[player.Y][player.X-1].X,dmap[player.Y][player.X-1].Y))

    if dmap[player.Y][player.X + 1].Content in goodTile and (player.X + 1, player.Y) not in invalidPos:
        possiblePosition.append((dmap[player.Y][player.X + 1].X,dmap[player.Y][player.X + 1].Y))

    if dmap[player.Y - 1][player.X].Content in goodTile and (player.X, player.Y-1) not in invalidPos:
        possiblePosition.append((dmap[player.Y - 1][player.X].X,dmap[player.Y - 1][player.X].Y))

    if dmap[player.Y + 1][player.X].Content in goodTile and (player.X, player.Y+1) not in invalidPos:
        possiblePosition.append((dmap[player.Y + 1][player.X].X,dmap[player.Y + 1][player.X].Y))

    return possiblePosition

@app.route("/", methods=["POST"])
def reponse():
    """
    Point d'entree appelle par le GameServer
    """
    return bot()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)