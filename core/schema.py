import pickle
import pytz
import graphene
from django.conf import settings
from core.models import Customer, Employee, SaleProduct, StockProduct, CardControl
from core.types import DynamicScalar


class EmployeeRole(graphene.Enum):
    RECEPTIONIST = 'receptionist'
    BARTENDER = 'bartender'
    CASHIER = 'cashier'
    MANAGER = 'manager'
    ADMIN = 'admin'
    CLEANING = 'cleaning'
    KITCHEN = 'kitchen'
    OTHER = 'other'


class StockProductType(graphene.ObjectType):
    id = graphene.ID()
    name = graphene.String()
    price = graphene.Float()
    stock = graphene.Int()


class SaleProductType(graphene.ObjectType):
    id = graphene.ID()
    name = graphene.String()
    price = graphene.Float()
    description = graphene.String()
    base_items = graphene.List(StockProductType)

    def resolve_base_items(self, info, **kwargs):
        return self.base_items.all()


class EmployeeType(graphene.ObjectType):
    id = graphene.ID()
    name = graphene.String()
    cpf = graphene.String()
    date_of_birth = graphene.Date()
    gender = graphene.Int()
    role = graphene.String()
    admission_date = graphene.Date()
    age = graphene.Int()
    address = graphene.String()


class CustomerType(graphene.ObjectType):
    name = graphene.String()
    rg = graphene.String()
    date_of_birth = graphene.Date()
    gender = graphene.Int()
    age = graphene.Int()
    visits = graphene.Int()


class CardControlType(graphene.ObjectType):
    code = graphene.Int()
    products = DynamicScalar()
    date_in = graphene.DateTime()
    date_out = graphene.DateTime()
    customer = graphene.Field(CustomerType)
    total_amount = graphene.Float()

    def resolve_products(self, info, **kwargs):
        return pickle.loads(self.products)

####################
#  ╔═╗ ╦ ╦╔═╗╦═╗╦ ╦
#  ║═╬╗║ ║║╣ ╠╦╝╚╦╝
#  ╚═╝╚╚═╝╚═╝╩╚═ ╩ 
####################
class Query(graphene.ObjectType):
    version = graphene.String()

    def resolve_version(self, info, **kwargs):
        return settings.VERSION

    stock_products = graphene.List(StockProductType)
    def resolve_stock_products(self, info, **kwargs):
        return StockProduct.objects.filter(**kwargs)

    sale_products = graphene.List(SaleProductType)
    def resolve_sale_products(self, info, **kwargs):
        return SaleProduct.objects.filter(**kwargs)

    employees = graphene.List(EmployeeType)
    def resolve_employees(self, info, **kwargs):
        return Employee.objects.filter(**kwargs)

    customers = graphene.List(CustomerType)
    def resolve_customers(self, info, **kwargs):
        return Customer.objects.filter(**kwargs)

    card_controls =graphene.List(CardControlType)
    def resolve_card_controls(self, info, **kwargs):
        return CardControl.objects.filter(**kwargs)


##########################
#  ╔╦╗╦ ╦╔╦╗╔═╗╔╦╗╦╔═╗╔╗╔
#  ║║║║ ║ ║ ╠═╣ ║ ║║ ║║║║
#  ╩ ╩╚═╝ ╩ ╩ ╩ ╩ ╩╚═╝╝╚╝
##########################
class OpenCardControl(graphene.relay.ClientIDMutation):
    card_control = graphene.Field(CardControlType)

    class Input:
        code = graphene.Int(required=True)
        date_in = graphene.DateTime(required=True)
        customer_rg = graphene.String(required=True)

    def mutate_and_get_payload(self, info, **kwargs):
        try:
            customer = Customer.objects.get(rg=kwargs['customer_rg'])
        except Customer.DoesNotExist:
            raise Exception('No customer registered for RG: ', kwargs['rg'])

        if CardControl.objects.filter(customer__rg=customer.rg, date_out__isnull=True).count() > 0:
            raise Exception('A card is already open for RG: ', customer.rg)

        card = CardControl.objects.create(
            code=kwargs['code'],
            date_in=kwargs['date_in'],
            customer=customer,
        )
        card.save()
        customer.visits += 1
        customer.save()

        return OpenCardControl(card)


class CloseCardControl(graphene.relay.ClientIDMutation):
    card_control = graphene.Field(CardControlType)

    class Input:
        code = graphene.Int(required=True)
        date_out = graphene.DateTime(required=True)

    def mutate_and_get_payload(self, info, **kwargs):
        try:
            card = CardControl.objects.get(code=kwargs['code'])
        except CardControl.DoesNotExist:
            raise Exception('No card open with code: ', kwargs['code'])

        if card.date_out is not None:
            raise Exception('This card is already closed')

        if kwargs['date_out'].astimezone(pytz.timezone('America/Sao_Paulo')) < card.date_in.astimezone(pytz.timezone('America/Sao_Paulo')):
            raise Exception('Invaid date out')

        card.date_out = kwargs['date_out']
        card.save()

        return OpenCardControl(card)


class AddProductToCard(graphene.relay.ClientIDMutation):
    card_control = graphene.Field(CardControlType)

    class Input:
        card_code = graphene.Int(required=True)
        product_id = graphene.ID(required=True)
        amount = graphene.Int(required=True)

    def mutate_and_get_payload(self, info, **kwargs):
        if kwargs['amount'] <= 0 :
            raise Exception('Invalid amount of products')
    
        try:
            card = CardControl.objects.get(code=kwargs['card_code'])
        except CardControl.DoesNotExist:
            raise Exception('No card with code: ', kwargs['card_code'])

        # Ensure card is open
        if card.date_out is not None:
            raise Exception('Card is already closed')

        try:
            product = SaleProduct.objects.get(id=kwargs['product_id'])
        except SaleProduct.DoesNotExist:
            raise Exception('Unknown product with id: ', kwargs['product_id'])


        card_products = pickle.loads(card.products)
        if product.id in card_products:
            card_products[product.id]['amount'] += kwargs['amount']
        else:
            card_products[product.id] = {
                'name': product.name,
                'price': product.price,
                'description': product.description,
                'amount': kwargs['amount']
            }
        card.total_amount += product.price * kwargs['amount']
        card.products = pickle.dumps(card_products)
        card.save()

        return AddProductToCard(card)


class CreateCustomer(graphene.relay.ClientIDMutation):
    customer = graphene.Field(CustomerType)

    class Input:
        name = graphene.String(required=True)
        rg = graphene.String(required=True)
        date_of_birth = graphene.Date(required=True)
        gender = graphene.Int()
        age = graphene.Int()

    def mutate_and_get_payload(self, info, **kwargs):
        customer = Customer.objects.create(**kwargs)
        customer.save()

        return CreateCustomer(customer)


class CreateSaleProduct(graphene.relay.ClientIDMutation):
    product = graphene.Field(SaleProductType)

    class Input:
        name = graphene.String(required=True)
        price = graphene.Float(required=True)
        description = graphene.String()
        base_items = graphene.List(graphene.ID, required=True)

    def mutate_and_get_payload(self, info, **kwargs):
        name = kwargs['name'].strip().title()
        if kwargs['price'] <= 0:
            raise Exception('Invalid product price')
        
        base = []
        for i in kwargs['base_items']:
            try:
                base_product = StockProduct.objects.get(id=i)
            except StockProduct.DoesNotExist:
                raise Exception('Unknow product woth id ', i)
            base.append(base_product)

        product = SaleProduct.objects.create(
            name=name,
            price=kwargs['price'],
            description=kwargs['description']
        )
        for base_item in base:
            product.base_items.add(base_item)
        product.save()

        return CreateSaleProduct(product)


class CreateStockProduct(graphene.relay.ClientIDMutation):
    product = graphene.Field(StockProductType)

    class Input:
        name = graphene.String(required=True)
        price = graphene.Float(required=True)
        amount = graphene.Int(required=True)

    def mutate_and_get_payload(self, info, **kwargs):
        name = kwargs['name'].strip().title()
        if kwargs['price'] <= 0:
            raise Exception('Invalid product price')
        
        if kwargs['amount'] <= 0:
            raise Exception('Invalid amount')

        product, _ = StockProduct.objects.get_or_create(name=name)
        product.price = kwargs['price']
        product.stock += kwargs['amount']
        product.save()

        return CreateStockProduct(product)


class CreateEmployee(graphene.relay.ClientIDMutation):
    employee = graphene.Field(EmployeeType)
    
    class Input:
        name = graphene.String(required=True)
        cpf = graphene.String(required=True)
        date_of_birth = graphene.Date()
        gender = graphene.Int()
        role = EmployeeRole(required=True)
        admission_date = graphene.Date(required=True)
        age = graphene.Int(required=True)
        address = graphene.String()

    def mutate_and_get_payload(self, info, **kwargs):
        employee = Employee.objects.create(**kwargs)
        employee.save()

        return CreateEmployee(employee)


class Mutation:
    create_employee = CreateEmployee.Field()
    create_stock_product = CreateStockProduct.Field()
    create_sale_product = CreateSaleProduct.Field()
    create_customer = CreateCustomer.Field()
    open_card_control = OpenCardControl.Field()
    close_card_control = CloseCardControl.Field()
    add_product_to_card = AddProductToCard.Field()
