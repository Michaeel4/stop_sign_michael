



'''
Michael Lenort


this class is used to initiate a new vehicle object, which makes it more easier to push several information to the
backend.
'''


class Vehicle:

    # default constructor
    def __init__(self, id, timestamp, direction,category,
            stoppedForMs, speed, minVelocity, stoppedDistance, convoyIndex, convoyType):
        self.id = id
        self.timestamp = timestamp
        self.locationID = 0
        self.direction = "front"
        self.category = category
        self.stoppedForMs = 0.0
        self.speed = speed
        self.stoppedDistance = stoppedDistance
        self.convoyIndex = convoyIndex
        self.convoyType = convoyType






