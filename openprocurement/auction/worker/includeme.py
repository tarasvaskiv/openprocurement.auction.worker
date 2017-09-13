from openprocurement.auction.includeme import _register
from openprocurement.auction.interfaces import IAuctionsServer
from openprocurement.auction.worker.views import includeme


def dgfOtherAssets(components):
    _register(components, 'dgfOtherAssets')
    server = components.queryUtility(IAuctionsServer)
    includeme(server)


def dgfFinancialAssets(components):
    _register(components, 'dgfFinancialAssets')
    server = components.queryUtility(IAuctionsServer)
    includeme(server)
