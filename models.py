
class Product:
    def __init__(self, id, title, cost, image, category, is_popular= False):
        self.id = id
        self.title = title
        self.cost = cost
        self.image = image
        self.category = category
        self.is_popular = is_popular
