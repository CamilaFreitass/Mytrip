from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, FloatField
from wtforms.validators import DataRequired, Length, Email, EqualTo, NumberRange



class FormCriarConta(FlaskForm):
    nome = StringField('Nome do viajante', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    senha = PasswordField('senha', validators=[DataRequired(), Length(6, 20)])
    confirmacao = PasswordField('Confirmação de Senha', validators=[DataRequired(), EqualTo('senha')])
    submit_criar_conta = SubmitField('Criar Conta')


class FormLogin(FlaskForm):
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    senha = PasswordField('Senha', validators=[DataRequired(), Length(6, 20)])
    lembrar_dados = BooleanField('Lembrar Dados de Acesso')
    submit_login = SubmitField('Logar')


class FormCriarViagem(FlaskForm):
    destino = StringField('Destino', validators=[DataRequired()])
    valor_total = FloatField('Valor Total', validators=[DataRequired(), NumberRange(min=0)])
    submit_viagem = SubmitField('Criar Viagem')


class FormCriarAtividade(FlaskForm):
    nome_atividade = StringField('Nome da atividade', validators=[DataRequired()])
    valor_atividade = FloatField('Valor (R$)', validators=[DataRequired()])
    submit_atividade = SubmitField('Salvar Atividade')