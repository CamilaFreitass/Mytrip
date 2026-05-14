from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, FloatField, DateField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, NumberRange, Optional
from constants import MOEDAS_DESTINO, MOEDAS_COMPARACAO, MOEDAS_ATIVIDADE



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
    valor_total = FloatField('Valor Total (R$)', validators=[DataRequired(), NumberRange(min=0)])
    moeda_destino = SelectField('Moeda do Destino', choices=MOEDAS_DESTINO, validators=[Optional()])
    moeda_comparacao = SelectField('Moeda de Comparação', choices=MOEDAS_COMPARACAO, default='USD')
    data_inicio = DateField('Data de Início', validators=[Optional()], format='%Y-%m-%d')
    data_fim = DateField('Data de Fim', validators=[Optional()], format='%Y-%m-%d')
    submit_viagem = SubmitField('Criar Viagem')


class FormCriarAtividade(FlaskForm):
    nome_atividade = StringField('Nome da atividade', validators=[DataRequired()])
    valor_atividade = FloatField('Valor', validators=[DataRequired()])
    moeda_inserida = SelectField('Moeda', choices=MOEDAS_ATIVIDADE, default='BRL')
    data_atividade = DateField('Data', validators=[Optional()], format='%Y-%m-%d')
    submit_atividade = SubmitField('Salvar Atividade')