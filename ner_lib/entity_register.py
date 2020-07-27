#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from . import entity

class EntityRegister(object):
    """ A class containing the index of all disambiguated entities. """

    def __init__(self):
        self.id2entity = {}
        self.entity2id = {}

    def insert_entity(self, _entity, _id):
        """ Insterts a preferred sense for a given entity into to the entity register. """
        assert isinstance(_entity, entity.Entity)
        assert isinstance(_id, int) or _id == None

        if _entity in self.entity2id:
            sense = self.entity2id[_entity]
            self.id2entity[sense].discard(_entity)
        self.entity2id[_entity] = _id
        if _id not in self.id2entity:
            self.id2entity[_id] = set()
        self.id2entity[_id].add(_entity)

    def __str__(self):
        return str(self.id2entity)
 
