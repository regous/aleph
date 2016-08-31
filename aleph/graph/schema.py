import logging

from aleph.graph.nodes import NodeType
from aleph.graph.edges import EdgeType

log = logging.getLogger(__name__)


EntityNode = NodeType('Entity', indices=['alephEntity'])
PhoneNode = NodeType('Phone')
EmailNode = NodeType('Email')
AddressNode = NodeType('Address')
CollectionNode = NodeType('Collection', indices=['alephCollection'],
                          node=False)
DocumentNode = NodeType('Document', indices=['alephDocument'])

LOCATED_AT = EdgeType('LOCATED_AT')
CONTACT_FOR = EdgeType('CONTACT_FOR')
MENTIONS = EdgeType('MENTIONS')
PART_OF = EdgeType('PART_OF', hidden=True)
AKA = EdgeType('AKA', key='alephId')
