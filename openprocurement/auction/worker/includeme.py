from openprocurement.auction.includeme import _register
from openprocurement.auction.interfaces import IAuctionsServer
from openprocurement.auction.worker.views import includeme


def english(components, procurement_method_types):
    for procurementMethodType in procurement_method_types:
        _register(components, procurementMethodType)
    server = components.queryUtility(IAuctionsServer)
    includeme(server)
