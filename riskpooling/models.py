from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
    Currency as c, currency_range
)
import random
from django.db import models as djmodels
from django.db import models as djmodels
from django.db.models import Q, Sum

author = 'Scott Claessens'

doc = """Risk-pooling game"""


class Constants(BaseConstants):
    name_in_url = 'riskpooling'
    players_per_group = 3
    num_rounds = 10


class Subsession(BaseSubsession):
    def vars_for_admin_report(self):
        aps = self.get_players()
        all_transfers = SendReceive.objects.filter(Q(sender__in=aps) | Q(receiver__in=aps)).values('sender__id_in_group',
                                                                                                   'receiver__id_in_group',
                                                                                                   'amount_sent',
                                                                                                   'amount_requested',
                                                                                                   'sender__group__id_in_subsession')

        return {'all_transfers': all_transfers}

    def creating_session(self):
        for p in self.get_players():
            p.participant.vars['herd_size'] = c(self.session.config['initialherd'])
            p.participant.vars['under_minimum_years_left'] = self.session.config['years_before_death']
            p.participant.vars['dead'] = False



class Group(BaseGroup):
    def no_requests(self):
        n = 0
        for p in self.get_players():
            if p.request is True:
                n += 1
        if n == 0:
            self.norequests = True
        else:
            self.norequests = False

    norequests = models.BooleanField()



class Player(BasePlayer):
    def set_under_minimum_years_left(self):
        self.under_minimum_years_left = self.participant.vars['under_minimum_years_left']

    def set_growth(self):
        self.herd_size_initial = self.participant.vars['herd_size']
        growth_rate = random.gauss(self.session.config['growth_rate_mean'], self.session.config['growth_rate_sd'])
        self.participant.vars['herd_size'] = self.participant.vars['herd_size'] + (growth_rate * self.participant.vars['herd_size'])
        if self.participant.vars['herd_size'] > c(self.session.config['maxherd']):
            self.participant.vars['herd_size'] = c(self.session.config['maxherd'])
        self.herd_size_after_growth = self.participant.vars['herd_size']
        if self.herd_size_after_growth < c(self.session.config['minherd']):
            self.under_minimum = True
        else:
            self.under_minimum = False

    def set_shock(self):
        if random.uniform(0, 1) < self.session.config['shock_rate']:
            self.shock_occurrence = True
            shock_size = random.gauss(self.session.config['shock_size_mean'], self.session.config['shock_size_sd'])
            self.participant.vars['herd_size'] = self.participant.vars['herd_size'] - (shock_size * self.participant.vars['herd_size'])
        else:
            self.shock_occurrence = False
        self.herd_size_after_shock = self.participant.vars['herd_size']
        if self.herd_size_after_shock < c(self.session.config['minherd']):
            self.under_minimum = True
        else:
            self.under_minimum = False

    under_minimum_years_left = models.PositiveIntegerField()

    herd_size_initial = models.CurrencyField()

    herd_size_after_growth = models.CurrencyField()

    shock_occurrence = models.BooleanField()

    herd_size_after_shock = models.CurrencyField()

    under_minimum = models.BooleanField()

    request = models.BooleanField(
        choices=[
            [True, 'Yes'],
            [False, 'No'],
                 ],
        widget=widgets.RadioSelect(),
        verbose_name="Would you like to make a request for cattle?"
    )
    sr_dump = models.CharField()

    request_player = models.IntegerField(widget=widgets.RadioSelect())

    request_amount = models.CurrencyField(
        min=c(1),
        verbose_name="How many cattle would you like to request from this player?"
    )



    def outgoing(self):
        tot_sent = (self.sender.aggregate(tot_sent=Sum('amount_sent'))['tot_sent'] or 0)
        self.participant.vars['herd_size'] -= tot_sent

    def incoming(self):
        tot_received = (self.receiver.aggregate(tot_received=Sum('amount_sent'))['tot_received'] or 0)
        self.participant.vars['herd_size'] += tot_received

    def final_herd_size(self):
        if self.participant.vars['herd_size'] > c(self.session.config['maxherd']):
            self.participant.vars['herd_size'] = c(self.session.config['maxherd'])
        self.herd_size_after_transfers = c(self.participant.vars['herd_size'])
        if self.herd_size_after_transfers < c(self.session.config['minherd']):
            self.under_minimum = True
            self.participant.vars['under_minimum_years_left'] -= 1
        else:
            self.under_minimum = False
            self.participant.vars['under_minimum_years_left'] = self.session.config['years_before_death']
        self.under_minimum_years_left = self.participant.vars['under_minimum_years_left']
        if self.participant.vars['under_minimum_years_left'] == 0:
            self.participant.vars['dead'] = True

    herd_size_after_transfers = models.CurrencyField()

    def is_playing(self):
        return self.participant.vars['dead'] is False


class SendReceive(djmodels.Model):
    receiver = djmodels.ForeignKey(Player, related_name='receiver')
    sender = djmodels.ForeignKey(Player, related_name='sender')
    amount_requested = models.IntegerField()
    amount_sent = models.IntegerField(blank=True)

