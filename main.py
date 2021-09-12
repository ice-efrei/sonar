import copy
import math
import threading

import pygame
import RPi.GPIO as GPIO
import time


pygame.init()

# GPIO Mode (BOARD / BCM)
GPIO.setmode(GPIO.BCM)

# set GPIO Pins
GPIO_TRIGGER = 18
GPIO_ECHO = 24

# set GPIO direction (IN / OUT)
GPIO.setup(GPIO_TRIGGER, GPIO.OUT)
GPIO.setup(GPIO_ECHO, GPIO.IN)

MAX_RANGE = 50  # in cm


def sonar_ping():
    """
    do a ping with a HC-SR04 sensor (source : https://raspberrypi-tutorials.fr/utilisation-dun-capteur-de-distance-raspberry-pi-capteur-ultrasonique-hc-sr04/)
    :return: distance of the pinged object, if nothing ping in 0.5 sec return -1
    """
    GPIO.output(GPIO_TRIGGER, True)
    time.sleep(0.00001)
    GPIO.output(GPIO_TRIGGER, False)

    StartTime = time.time()
    StopTime = time.time()

    TimeElapsed = 0

    while GPIO.input(GPIO_ECHO) == 0:
        StartTime = time.time()

    TimeElapsed = StopTime - StartTime

    while GPIO.input(GPIO_ECHO) == 1 and TimeElapsed < 0.5:
        StopTime = time.time()
        TimeElapsed = StopTime - StartTime

    # the scan stop after 1 sec
    if TimeElapsed > 0.5:
        return -1

    distance = (TimeElapsed * 34300) / 2

    return distance


def angle_to_percent(angle):
    """
    convert an angle in degree to percent (source : https://raspberry-pi.fr/servomoteur-raspberry-pi/)
    :param angle: angle in degree
    :return: angle in percent
    """
    if angle > 180 or angle < 0:
        return False

    start = 4
    end = 12.5
    ratio = (end - start) / 180  # Calcul ratio from angle to percent

    angle_as_percent = angle * ratio

    return start + angle_as_percent


def move(current_angle, max_angle, angle, direction, pwm):
    if not(0 < current_angle + direction*angle < max_angle):
        direction = 1 if direction < 0 else -1

    current_angle = current_angle + direction * angle
    # print(current_angle)
    pwm.ChangeDutyCycle(angle_to_percent(current_angle))

    return current_angle, max_angle, direction


def draw_point(x, y, color, screen):
    for i in range(x - 1, x + 1):
        for j in range(y - 1, y + 1):
            screen.set_at((i, j), color)


def async_ping(point_list, run):
    print("async_ping")
    dist = sonar_ping()
    if dist > 0:
        point_list.append({
            'y': copy.deepcopy(dist),
            'alpha': copy.deepcopy(current_angle),
            'opacity': 1.0
        })
    time.sleep(0.5)
    if run:
        threading.Thread(target=async_ping, args=(point_list, run, )).start()


if __name__ == '__main__':
    width, height = 1000, 500
    screen = pygame.display.set_mode([width, height])

    run = True
    # point define as an angle and a distance
    points = [
        {'y': 30, 'alpha': 60, 'opacity': 1.0},
        {'y': 10, 'alpha': 160, 'opacity': 1.0},
        {'y': 10, 'alpha': 50, 'opacity': 1.0},
        {'y': 25, 'alpha': 75, 'opacity': 1.0}
    ]

    current_angle = 0
    direction = 1
    max_angle = 180

    pwm_gpio = 25
    frequence = 50
    GPIO.setup(pwm_gpio, GPIO.OUT)
    pwm = GPIO.PWM(pwm_gpio, frequence)

    pwm.start(angle_to_percent(0))

    # ping = threading.Thread(target=async_ping, args=(points, run,))
    # ping.start()

    try:
        while run:
            dist = sonar_ping()
            if dist > 0:
                points.append({
                    'y': copy.deepcopy(dist),
                    'alpha': copy.deepcopy(current_angle),
                    'opacity': 1.0
                })
            time.sleep(0.5)

            current_angle, max_angle, direction = move(current_angle, max_angle, 5, direction, pwm)

            # system to display all points and make those disappear
            for point in points:
                y = int((point['y']/MAX_RANGE)*height)
                try:
                    x = int(
                        ((point['y']/MAX_RANGE)*(width/2)) / math.tan(math.radians(point['alpha']))
                    ) + int(width/2)
                except ZeroDivisionError:
                    x = 0
                color = [int(255 * point['opacity'])] * 3
                # print("x : ", x, " - y : ", y)
                draw_point(x, y, color, screen)
                point['opacity'] = point['opacity']-0.2
                if point['opacity'] < 0:
                    points.pop(points.index(point))

            # handle window closing
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    run = False

            # print("pygame loop")

            pygame.display.flip()
    except KeyboardInterrupt:  # ctrl + c
        print("Measurement stopped by User")
        GPIO.cleanup()

    pwm.stop()
    pygame.quit()
    GPIO.cleanup()
