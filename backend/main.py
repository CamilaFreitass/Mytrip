#obs.: como estamos importando do arquivo __init__.py (e é ele roda o projeto) não precisa citar i arquivo
#  se esstivessemos importando de outro arquivo, dai seria assim: ex. from trip.models import Viajante
from trip import app


if __name__ == '__main__':
    app.run(debug=True)


