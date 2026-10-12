from django import forms


class AskForm(forms.Form):
    model = forms.ChoiceField(label="選擇模型", choices=[])
    question = forms.CharField(
        label="你的問題", max_length=4000, strip=True,
        widget=forms.Textarea(attrs={"rows": 6, "placeholder": "例如：如何查看 Linux 的磁碟使用量？"}),
    )

    def __init__(self, *args, model_names=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["model"].choices = [(name, name) for name in model_names]
