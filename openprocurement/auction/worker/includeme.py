from openprocurement.auction.includeme import _register


def belowThreshold(components):
    _register(components, 'belowThreshold')


def aboveThresholdUA(components):
    _register(components, 'aboveThresholdUA')


def aboveThresholdEU(components):
    _register(components, 'aboveThresholdEU')


def competitiveDialogueEU(components):
    _register(components, 'competitiveDialogueEU.stage2')


def competitiveDialogueUA(components):
    _register(components, 'competitiveDialogueUA.stage2')


def aboveThresholdUAdefense(components):
    _register(components, 'aboveThresholdUA.defense')
