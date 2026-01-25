"""
Project forms.
"""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, IntegerField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class ProjectForm(FlaskForm):
    """Form for creating/editing projects."""
    name = StringField('Project Name', validators=[
        DataRequired(),
        Length(min=1, max=100)
    ])
    description = TextAreaField('Description', validators=[
        Length(max=500)
    ])
    k_factor = IntegerField('K-Factor', validators=[
        NumberRange(min=1, max=100, message='K-factor must be between 1 and 100')
    ], default=32)
    default_rating = IntegerField('Default Rating', validators=[
        NumberRange(min=0, max=5000, message='Default rating must be between 0 and 5000')
    ], default=1000)
    allow_ties = BooleanField('Allow Ties', default=True)
    item_type = StringField('Item Type Label', validators=[
        Length(max=50)
    ], default='item')
    submit = SubmitField('Save')


class ItemForm(FlaskForm):
    """Form for adding/editing items."""
    name = StringField('Item Name', validators=[
        DataRequired(),
        Length(min=1, max=200)
    ])
    notes = TextAreaField('Notes', validators=[
        Length(max=500)
    ])
    submit = SubmitField('Save')


class ImportForm(FlaskForm):
    """Form for importing items."""
    file = FileField('File', validators=[
        FileAllowed(['txt', 'csv', 'json'], 'Only .txt, .csv, and .json files are allowed')
    ])
    text_content = TextAreaField('Or paste content here', validators=[
        Length(max=50000)
    ])
    import_format = SelectField('Format', choices=[
        ('auto', 'Auto-detect'),
        ('txt', 'Text (one item per line)'),
        ('csv', 'CSV (name, rating, notes columns)'),
        ('json', 'Legacy JSON ({name: rating})')
    ])
    submit = SubmitField('Import')
