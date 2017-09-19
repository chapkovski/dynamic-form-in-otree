import floppyforms.__future__ as forms
from .models import SendReceive, Player

from django.forms import inlineformset_factory, BaseFormSet, BaseInlineFormSet


class SRForm(forms.ModelForm):
    class Meta:
        model = SendReceive
        fields = ['amount_sent']

    def __init__(self, *args, **kwargs):
        super(SRForm, self).__init__(*args, **kwargs)
        curmax = int(kwargs['instance'].sender.participant.vars['herd_size'])
        self.fields['amount_sent'] = forms.IntegerField(label='How much to sent?',
                                                        required=True,
                                                        max_value=curmax,
                                                        min_value=0,
                                                        )


class BaseSRFormset(BaseInlineFormSet):
    def clean(self):
        if any(self.errors):
            return
        tot_amount_sent = 0
        for form in self.forms:
            tot_amount_sent += form.cleaned_data['amount_sent']
        max_sent = int(self.instance.participant.vars['herd_size'])
        if tot_amount_sent > max_sent:
            raise forms.ValidationError("The maximum amount you can send is {}".format(max_sent))


SRFormSet = inlineformset_factory(Player, SendReceive,
                                  fk_name='sender',
                                  can_delete=False,
                                  extra=0,
                                  form=SRForm,
                                  formset=BaseSRFormset)
