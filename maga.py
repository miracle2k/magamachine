import click
import subprocess
import pygame
import glob
from datetime import datetime, timedelta
import button
import math
import random
import os
import itertools
from pygame.locals import *


LETTERS = [chr(x) for x in range(ord('A'), ord('Z')+1)]


class RenderedSymbols:
    def __init__(self):
        self.db = {}

    def add(self, letter, surface):
        self.db[letter] = surface

    def get(self, letter):
        return self.db[letter]


rendered_symbols = RenderedSymbols()


class Reel():
    def __init__(self, machine, idx, symbols=LETTERS, default=0):
        # Position assumes the center of a slot
        self.idx = idx
        self.machine = machine
        self.symbols = symbols    

        # The position is an index in the list of symbols. If it
        # is not a natural number, it means: the reel is in-between 
        # symbols.
        self.position = default

    def layout(self, machine_rect):        
        width = machine_rect.width / float(self.machine.num_reels)
        reel_rect = pygame.Rect(self.idx * width, 0, width, machine_rect.height)
        self.rect = reel_rect

    def norm_idx(self, idx):
        while idx >= len(self.symbols):
            idx = idx - len(self.symbols)
        while idx < 0:
            idx = len(self.symbols) + idx
        return idx

    def get_symbol_index(self, symbol):
        if isinstance(symbol, (float,)):
            symbol_idx = int(symbol * len(self.symbols))
            symbol = self.symbols[symbol_idx]
            # HACK: Do not allow G
            if symbol == 'G':
                symbol = 'H'
        return self.symbols.index(symbol)

    def count_from_to(self, start, end):
        start = self.norm_idx(start)
        end = self.norm_idx(end)
        if end > start:
            return end - start
        else:
            return len(self.symbols) - start + end

    def draw(self, target):
        current_symbol_idx = int(round(self.position))
        remainder = self.position - current_symbol_idx

        # We have to draw the current position, and a certain amount before/after
        # If the position is 10, we draw 9 10 11
        # If the position is 10.6, we draw 10, 11, 12
        num_before_after = 1        
        symbols_to_draw = [self.norm_idx(x) for x in range(current_symbol_idx-num_before_after, current_symbol_idx+num_before_after+1)]
        
        # eg. will be: -2, -1, 0, 1, 2
        shift = list(range(-(len(symbols_to_draw)/2), len(symbols_to_draw)/2 + 1))

        for shift, symbol_idx in zip(shift, symbols_to_draw):
            letter_surface = rendered_symbols.get(self.symbols[symbol_idx])
            font_rect = letter_surface.get_rect()
            font_rect.centerx = self.rect.centerx

            font_rect.top = (
                # Center in the middle of our target rect
                self.rect.height / 2 
                # Center each symbol at the rect center
                - self.machine.symbol_height / 2 
                # Which symbol 
                + shift * self.machine.symbol_height
                # How far long we are to the next one
                - remainder * self.machine.symbol_height
            )
            
            target.blit(letter_surface, font_rect)    


MACHINEBG = (223,223,223)


class SlotMachine(object):

    def __init__(self, symbol_height, symbol_width, speed=9):
        self.symbol_width = symbol_width
        self.symbol_height = symbol_height
        self.reels = []
        self.speed = speed
        self.bg_color = MACHINEBG

        self.on_spin_end = None

    @property
    def num_reels(self):
        return len(self.reels)

    def add_reel(self, symbols=None):
        if not symbols:
            symbols = LETTERS

        self.reels.append(Reel(
            self, 
            self.num_reels, 
            symbols=symbols))

    def layout(self, screen_rect):
        machine_height = self.symbol_height * 1
        machine_width = self.symbol_width * self.num_reels
        
        # Center the slot machine in the frame
        machine_rect = pygame.Rect(0, 0, machine_width, machine_height)
        machine_rect.center = screen_rect.center
        self.rect = machine_rect
        self.surface = pygame.Surface((machine_rect.width, machine_rect.height))
        #self.surface.set_alpha(170)

        for reel in self.reels:
            reel.layout(self.rect)

    @property
    def is_spinning(self):
        return sum(self.desired_spin_distances) > 0

    def set_to(self, targets):
        self.targets = [
            self.reels[idx].symbols.index(target) 
            for idx, target in enumerate(targets)]

        for reel, target_idx in zip(self.reels, self.targets):
            reel.position = target_idx

        self.desired_spin_distances = [0] * self.num_reels

    def spin_to(self, targets, durations):
        if self.is_spinning:
            print('already spinning')
            return

        # stop at "targets". stop in the given order, and with the given durations in between.
        self.targets = [
            self.reels[idx].get_symbol_index(target) 
            for idx, target in enumerate(targets)]

        # pre-calculate how far every reel has to spin
        total_slots_to_spin = []
        for idx, d in enumerate(durations):
            by_speed = self.speed * d
            extra_to_target = self.reels[idx].count_from_to(self.reels[idx].position + by_speed, self.targets[idx])            

            total_slots_to_spin.append(by_speed + extra_to_target)
        
        self.desired_spin_distances = total_slots_to_spin    

    def update(self, time):
        was_spinning = self.is_spinning

        for idx, reel in enumerate(self.reels):
            max_allowed = self.desired_spin_distances[idx]
            to_spin = min(max_allowed, self.speed * time)

            reel.position += to_spin

            reel.position = reel.norm_idx(reel.position)
            self.desired_spin_distances[idx] -= to_spin

        if was_spinning and not self.is_spinning:
            if self.on_spin_end:
                self.on_spin_end()

    def draw(self, target):
        #self.surface.fill((233,0,255))
        #self.surface.fill((187,19,62))
        self.surface.fill(self.bg_color)

        for reel in self.reels:
            # we could use clamp here
            reel.draw(self.surface)

        target.blit(self.surface, self.rect)


def create_letters(font):
    # Create all the letters
    letters = []
    for x in itertools.chain(LETTERS,  ['#']):
        surface = font.render(x, 1, (10, 10, 10))
        #surface.set_alpha(255)
        letters.append(surface)
        rendered_symbols.add(x, surface)

    # Find the maximum letter size
    max_width = max_height = None
    for letter in letters:
        width, height = letter.get_size()
        max_width = max(max_width, width)
        max_height = max(max_width, height)

    return max_width, max_height


def getfilepath(filename):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), filename)


def load_spin_effects():
    effects = []
    for file in glob.glob(getfilepath('wav/*')):
        print "Loading effect", getfilepath(file)
        effects.append(pygame.mixer.Sound(getfilepath(file)))
    return effects


class Callbacks:
    def __init__(self):
        self.list = []

    def schedule(self, from_now_seconds, callback):
        dt = datetime.utcnow() + timedelta(seconds=from_now_seconds)
        self.list.append((dt, callback))

    def handle(self):
        l = self.list[::]
        now = datetime.utcnow()
        to_remove = set()
        for item in l:
            dt, callback = item
            if dt < now:
                callback()
                to_remove.add(item)
        self.list = list(set(self.list) - to_remove)


class SurfaceFade:
    def __init__(self, surface, rect):
        self.rect = rect
        self.surface = surface
        self.remaining = 0
        self.total = 0

    def update(self, time):
        was_spinning = self.is_spinning

        for idx, reel in enumerate(self.reels):
            max_allowed = self.desired_spin_distances[idx]
            to_spin = min(max_allowed, self.speed * time)

            reel.position += to_spin

            reel.position = reel.norm_idx(reel.position)
            self.desired_spin_distances[idx] -= to_spin

        if was_spinning and not self.is_spinning:
            if self.on_spin_end:
                self.on_spin_end()
                
    def start(self, seconds):
        self.remaining = seconds
        self.total = seconds

    def reset(self):
        self.total = 0

    def update(self, time):
        if self.total:
            self.remaining -= time
            if self.remaining < 0:
                self.remaining = 0

    def draw(self, target):
        if not self.total:
            alpha = 255
        else:
            alpha = ((self.remaining / self.total)) * 255
        self.surface.set_alpha(alpha)
        target.blit(self.surface, (0, 0))


@click.command()
@click.option('--fullscreen', is_flag=True)
@click.option('--fps', is_flag=True)
@click.option('--size')
@click.option('--threshold', type=float, default=0.15)
@click.option('--picfile', default=getfilepath('trump800.jpg'))
@click.option('--printer-mac', default="C4:30:18:35:13:FA")
@click.option('--speedup', type=int, default=2)
@click.option('--reelspeed', type=int, default=9)
def main(fullscreen=False, fps=False, size=None, picfile=None, printer_mac=None, threshold=None, speedup=None, reelspeed=None):
    print('- Picfile: %s' % picfile)
    assert os.path.exists(picfile)    

    # Initialise screen
    pygame.init()
    flags = pygame.DOUBLEBUF
    if fullscreen:
        flags |= pygame.FULLSCREEN
    pygame.mouse.set_visible(False)
    screen = pygame.display.set_mode((1920, 1080), flags)
    pygame.display.set_caption('#MAGA Machine')

    spin_effects = load_spin_effects()
    random.shuffle(spin_effects)

    # Fill background
    background = pygame.Surface(screen.get_size())
    background = background.convert()
    background.fill((255, 255, 255))    
    
    font = pygame.font.Font(getfilepath("./bender_bold.ttf"), size or 220)
    fontSmall = pygame.font.Font(None, 33)
    fontPrompt = pygame.font.Font(getfilepath("./avenir.ttf"), 70)    

    symbol_width, symbol_height = create_letters(font)
    padding = 0.1
    symbol_width = int(symbol_width + padding * symbol_width)

    machine = SlotMachine(symbol_height, symbol_width, speed=reelspeed)
    machine.add_reel(symbols=LETTERS + ['#'])
    machine.add_reel()
    machine.add_reel()
    machine.add_reel()
    machine.add_reel()
    machine.set_to('#MAGA')
    machine.layout(background.get_rect())

    reel_sound = pygame.mixer.Sound(getfilepath('bg2loud.wav'))
    reel_sound.set_volume(0.35)
    bg_image = pygame.image.load(getfilepath('bg.jpg'))
    bg_surface = SurfaceFade(bg_image, screen.get_rect())
    win_image = pygame.image.load(getfilepath('winimg.jpg'))
    lose_sound = pygame.mixer.Sound(getfilepath('lose1.wav'))
    win_sound = pygame.mixer.Sound(getfilepath('win2.wav'))

    callbacks = Callbacks()

    CURRENT_GAME = dict()
    def stop_current_game():
        for x in CURRENT_GAME.copy():
            del CURRENT_GAME[x]

    def start_current_game(**kw):
        for x in CURRENT_GAME.copy():
            del CURRENT_GAME[x]
        CURRENT_GAME['on'] = True
        CURRENT_GAME.update(kw)


    def end_game():        
        print('Game ended')
        stop_current_game()
        machine.bg_color = MACHINEBG
        bg_surface.reset()
        button.set_led(True)


    def handle_spin_end():        
        print('Spinning is done.')
        
        reel_sound.fadeout(1000)
        
        if CURRENT_GAME.get('win'):
            CURRENT_GAME['final'] = True
            bg_surface.start(3)
            machine.bg_color = (255,255,255)
            win_sound.play()    
            def cb():
                end_game()
            callbacks.schedule(16, cb)
            def cb2():
                CURRENT_GAME['prompt'] = True
            callbacks.schedule(5, cb2)
        else:
            lose_sound.play()
            end_game()
        

    machine.on_spin_end = handle_spin_end

    def sendprint():
        if not printer_mac:
            print('Skip printing, no mac')
            return

        print('Printing...')
        pp = subprocess.Popen(["obexftp", "--nopath", "--noconn", "--uuid", "none", "--bluetooth", printer_mac,  "--channel", "4", "-p", picfile])

    def spin():
        if machine.is_spinning:
            print('already spinning')
            return
        if CURRENT_GAME.get('on', False):
            print('have an active game')
            return

        r = random.random()

        reel_sound.play()
        spin_effects[int(r*len(spin_effects))].play()

        
        print('Dice is ', r, 'threshold is', threshold)
        extra_time_for_g = 0
        if r < threshold:
            print('ITS A WIN!!!')
            target = 'G'
            extra_time_for_g = 3
            start_current_game(win=True)
            sendprint()
        else:
            start_current_game(win=False)
            target = random.random()

        button.set_led(False)
        machine.spin_to(
            ['#', 'M', 'A', target, 'A'],
            [4/speedup,   5.5/speedup,    7/speedup,  10/speedup + extra_time_for_g,      8/speedup]
        )

    # Init LED
    button.set_led(True)

    # Event loop
    clock = pygame.time.Clock()

    screen.blit(bg_image, (0, 0))

    refresh_bg = False
    while True:
        elapsed_ms = clock.tick(120)
        elapsed_s = elapsed_ms / 1000.0

        callbacks.handle()

        # HANDLE EVENTS
        if button.query():
            spin()
        for event in pygame.event.get():
            if event.type == QUIT:
                return

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return

                if event.key == pygame.K_DOWN:
                    spin()

        # TICK ALL OBJECTS
        machine.update(elapsed_s)
        bg_surface.update(elapsed_s)

        # DRAW
        if CURRENT_GAME.get('on') and CURRENT_GAME.get('final'):
            refresh_bg = True            
            screen.blit(background, (0, 0))
            bg_surface.draw(screen)

            # Show america great again as a text?
            #screen.blit(win_image, (machine.rect.left, machine.rect.top))
            machine.draw(screen)

            if CURRENT_GAME.get('prompt'):
                prompt1 = fontPrompt.render('Please wait for your prize to print (about 15 seconds).', 1, (120, 120, 120))
                promptRect = prompt1.get_rect()
                promptRect.center = screen.get_rect().center
                promptRect.top += 200
                screen.blit(prompt1, promptRect)

                prompt2 = fontPrompt.render('Do not pull the paper during printing.', 1, (120, 120, 120))
                promptRect = prompt2.get_rect()
                promptRect.center = screen.get_rect().center
                promptRect.top += 280
                screen.blit(prompt2, promptRect)
        else:
            if refresh_bg:
                bg_image.set_alpha(255)
                screen.blit(bg_image, (0, 0))
                refresh_bg = False

            machine.draw(screen)

        if fps:
            pygame.draw.rect(screen, (255,255,255), pygame.Rect(0, 0, 200, 50))
            screen.blit(fontSmall.render('FPS: %s' % clock.get_fps(), 1, (10, 10, 10)), pygame.Rect(0, 0, 200, 50))
            #pygame.display.update(pygame.Rect(0, 0, 200, 50))

        #pygame.display.update(pygame.Rect(0, 0, 200, 50))
        pygame.display.flip()


if __name__ == '__main__': 
    button.setup()
    try:
        main()
    finally:
        button.cleanup()
