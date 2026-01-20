from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from main.models import Category, Product, Wallet
from decimal import Decimal

# Cloudinary placeholder URL
PLACEHOLDER_IMAGE = 'https://res.cloudinary.com/dplyxhcu1/image/upload/v1768127190/placeholder_akzwmb.png'


class Command(BaseCommand):
    help = 'Populate store with categories and products'

    def handle(self, *args, **options):
        self.stdout.write('Starting data population...\n')
        
        # Create admin user if doesn't exist
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@techfy.africa',
                'is_staff': True,
                'is_superuser': True,
                'first_name': 'Admin',
                'last_name': 'User'
            }
        )
        if created:
            admin.set_password('admin123')
            admin.save()
            self.stdout.write(self.style.SUCCESS(f'✓ Created admin user (username: admin, password: admin123)'))
        else:
            self.stdout.write(f'✓ Admin user already exists')
        
        # Create wallet for admin
        Wallet.objects.get_or_create(user=admin, defaults={'balance': 1000000})
        
        # Create Categories
        categories_data = [
            {'name': 'Electronics', 'description': 'Phones, Laptops, TVs and more'},
            {'name': 'Fashion', 'description': 'Clothing, Shoes and Accessories'},
            {'name': 'Home & Garden', 'description': 'Furniture, Decor and Tools'},
            {'name': 'Sports & Fitness', 'description': 'Sports equipment and fitness gear'},
            {'name': 'Books & Media', 'description': 'Books, Music and Movies'},
            {'name': 'Toys & Games', 'description': 'Toys, Games and Hobbies'},
            {'name': 'Health & Beauty', 'description': 'Skincare, Makeup and Wellness'},
            {'name': 'Discounted Items', 'description': 'Special offers and discounts'},
        ]
        
        categories = {}
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            categories[cat_data['name']] = category
            status = 'Created' if created else 'Exists'
            self.stdout.write(f'  {status}: {category.name}')
        
        self.stdout.write('\n')
        
        # Create Products
        products_data = [
            # Electronics (with some discounts)
            {
                'name': 'iPhone 14 Pro Max',
                'description': 'Latest Apple iPhone with A16 Bionic chip, 6.7" display, and advanced camera system',
                'price': 850000,
                'stock': 15,
                'category': 'Electronics',
                'discount': 5,
                'featured': True
            },
            {
                'name': 'Samsung Galaxy S23 Ultra',
                'description': 'Premium Android phone with S Pen, 200MP camera, and powerful Snapdragon processor',
                'price': 780000,
                'stock': 20,
                'category': 'Electronics',
                'discount': 10,
                'featured': True
            },
            {
                'name': 'MacBook Air M2',
                'description': 'Ultra-thin laptop with M2 chip, 13.6" Liquid Retina display, 8GB RAM, 256GB SSD',
                'price': 1200000,
                'stock': 10,
                'category': 'Electronics',
                'discount': 0,
                'featured': True
            },
            {
                'name': 'Dell XPS 15',
                'description': 'Powerful Windows laptop with Intel i7, 16GB RAM, 512GB SSD, NVIDIA graphics',
                'price': 950000,
                'stock': 12,
                'category': 'Electronics',
                'discount': 15,
                'featured': False
            },
            {
                'name': 'Sony WH-1000XM5 Headphones',
                'description': 'Premium noise-cancelling wireless headphones with exceptional sound quality',
                'price': 285000,
                'stock': 30,
                'category': 'Electronics',
                'discount': 20,
                'featured': True
            },
            {
                'name': 'iPad Pro 12.9"',
                'description': 'Powerful tablet with M2 chip, Liquid Retina XDR display, Apple Pencil support',
                'price': 650000,
                'stock': 18,
                'category': 'Electronics',
                'discount': 0,
                'featured': False
            },
            {
                'name': 'Apple Watch Series 9',
                'description': 'Advanced smartwatch with fitness tracking, ECG, always-on display',
                'price': 320000,
                'stock': 25,
                'category': 'Electronics',
                'discount': 8,
                'featured': True
            },
            {
                'name': 'AirPods Pro 2nd Gen',
                'description': 'Wireless earbuds with active noise cancellation and spatial audio',
                'price': 195000,
                'stock': 40,
                'category': 'Electronics',
                'discount': 0,
                'featured': False
            },
            
            # Fashion
            {
                'name': 'Nike Air Max 270',
                'description': 'Comfortable running shoes with Air cushioning and breathable mesh upper',
                'price': 85000,
                'stock': 50,
                'category': 'Fashion',
                'discount': 25,
                'featured': False
            },
            {
                'name': 'Levi\'s 501 Original Jeans',
                'description': 'Classic straight-fit jeans, 100% cotton denim, multiple sizes available',
                'price': 45000,
                'stock': 100,
                'category': 'Fashion',
                'discount': 0,
                'featured': False
            },
            {
                'name': 'Designer Leather Handbag',
                'description': 'Premium genuine leather handbag with multiple compartments',
                'price': 120000,
                'stock': 25,
                'category': 'Fashion',
                'discount': 30,
                'featured': True
            },
            {
                'name': 'Ray-Ban Aviator Sunglasses',
                'description': 'Classic aviator sunglasses with UV protection and polarized lenses',
                'price': 75000,
                'stock': 35,
                'category': 'Fashion',
                'discount': 15,
                'featured': False
            },
            
            # Home & Garden
            {
                'name': 'Smart LED TV 55"',
                'description': '4K UHD Smart TV with HDR, built-in streaming apps, voice control',
                'price': 380000,
                'stock': 15,
                'category': 'Home & Garden',
                'discount': 12,
                'featured': True
            },
            {
                'name': 'Ergonomic Office Chair',
                'description': 'Comfortable office chair with lumbar support, adjustable height and armrests',
                'price': 95000,
                'stock': 40,
                'category': 'Home & Garden',
                'discount': 0,
                'featured': False
            },
            {
                'name': 'Robot Vacuum Cleaner',
                'description': 'Smart robot vacuum with app control, automatic charging, HEPA filter',
                'price': 185000,
                'stock': 20,
                'category': 'Home & Garden',
                'discount': 18,
                'featured': False
            },
            {
                'name': 'Coffee Maker Deluxe',
                'description': 'Programmable coffee maker with thermal carafe, 12-cup capacity',
                'price': 55000,
                'stock': 30,
                'category': 'Home & Garden',
                'discount': 10,
                'featured': False
            },
            
            # Sports & Fitness
            {
                'name': 'Adjustable Dumbbells Set',
                'description': 'Professional dumbbells with adjustable weight 5-25kg, compact design',
                'price': 75000,
                'stock': 30,
                'category': 'Sports & Fitness',
                'discount': 10,
                'featured': False
            },
            {
                'name': 'Yoga Mat Premium',
                'description': 'Non-slip yoga mat with carrying strap, eco-friendly material, 6mm thick',
                'price': 15000,
                'stock': 100,
                'category': 'Sports & Fitness',
                'discount': 0,
                'featured': False
            },
            {
                'name': 'Fitness Tracker Watch',
                'description': 'Water-resistant fitness tracker with heart rate monitor and sleep tracking',
                'price': 45000,
                'stock': 50,
                'category': 'Sports & Fitness',
                'discount': 20,
                'featured': True
            },
            
            # Books & Media
            {
                'name': 'Kindle Paperwhite',
                'description': 'E-reader with 6.8" glare-free display, waterproof, weeks of battery life',
                'price': 125000,
                'stock': 35,
                'category': 'Books & Media',
                'discount': 15,
                'featured': True
            },
            {
                'name': 'Bestseller Book Collection',
                'description': 'Set of 5 bestselling novels, hardcover editions',
                'price': 35000,
                'stock': 50,
                'category': 'Books & Media',
                'discount': 0,
                'featured': False
            },
            {
                'name': 'Bluetooth Speaker Portable',
                'description': 'Waterproof wireless speaker with 24-hour battery life',
                'price': 65000,
                'stock': 45,
                'category': 'Books & Media',
                'discount': 12,
                'featured': False
            },
            
            # Toys & Games
            {
                'name': 'PlayStation 5',
                'description': 'Latest gaming console with ultra-fast SSD, 4K gaming, DualSense controller',
                'price': 520000,
                'stock': 8,
                'category': 'Toys & Games',
                'discount': 0,
                'featured': True
            },
            {
                'name': 'LEGO Star Wars Set',
                'description': 'Large Star Wars building set with 1000+ pieces, includes minifigures',
                'price': 85000,
                'stock': 25,
                'category': 'Toys & Games',
                'discount': 20,
                'featured': False
            },
            {
                'name': 'Nintendo Switch OLED',
                'description': 'Hybrid gaming console with 7" OLED screen, Joy-Con controllers',
                'price': 280000,
                'stock': 15,
                'category': 'Toys & Games',
                'discount': 5,
                'featured': True
            },
            
            # Health & Beauty
            {
                'name': 'Skincare Gift Set',
                'description': 'Complete skincare routine with cleanser, serum, moisturizer, and sunscreen',
                'price': 65000,
                'stock': 45,
                'category': 'Health & Beauty',
                'discount': 15,
                'featured': False
            },
            {
                'name': 'Electric Toothbrush Pro',
                'description': 'Sonic toothbrush with 5 modes, smart timer, 2-week battery life',
                'price': 45000,
                'stock': 60,
                'category': 'Health & Beauty',
                'discount': 0,
                'featured': False
            },
            {
                'name': 'Hair Dryer Professional',
                'description': 'Ionic hair dryer with multiple heat settings and cool shot button',
                'price': 55000,
                'stock': 35,
                'category': 'Health & Beauty',
                'discount': 18,
                'featured': False
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for product_data in products_data:
            product, created = Product.objects.update_or_create(
                name=product_data['name'],
                defaults={
                    'description': product_data['description'],
                    'price': Decimal(str(product_data['price'])),
                    'stock': product_data['stock'],
                    'category': categories[product_data['category']],
                    'seller': admin,
                    'discount_percentage': Decimal(str(product_data['discount'])),
                    'is_featured': product_data['featured'],
                    'cloudinary_url': PLACEHOLDER_IMAGE,  # Use Cloudinary placeholder
                }
            )
            
            if created:
                created_count += 1
                status_icon = '✓'
                status_text = 'Created'
            else:
                updated_count += 1
                status_icon = '↻'
                status_text = 'Updated'
            
            # Display with discount info
            if product_data['discount'] >= 10:
                discounted_price = product.get_discounted_price()
                self.stdout.write(
                    self.style.WARNING(
                        f'  {status_icon} {status_text}: {product.name} '
                        f'(₦{product.price:,.2f} → ₦{discounted_price:,.2f} '
                        f'- {product.discount_percentage}% OFF) [DISCOUNTED]'
                    )
                )
            else:
                self.stdout.write(f'  {status_icon} {status_text}: {product.name} (₦{product.price:,.2f})')
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'\n✓ Successfully created {created_count} new products!'))
        if updated_count > 0:
            self.stdout.write(self.style.WARNING(f'✓ Updated {updated_count} existing products!'))
        self.stdout.write(f'✓ Total products in database: {Product.objects.count()}')
        self.stdout.write(f'✓ Total categories: {Category.objects.count()}')
        
        # Show discount summary
        discounted_products = Product.objects.filter(discount_percentage__gt=0).order_by('-discount_percentage')
        if discounted_products.exists():
            self.stdout.write(f'\n Discounted Products: {discounted_products.count()}')
            for product in discounted_products:
                savings = product.get_savings()
                self.stdout.write(
                    f'   • {product.name}: {product.discount_percentage}% off '
                    f'(Save ₦{savings:,.2f})'
                )
        
        # Show featured products
        featured_products = Product.objects.filter(is_featured=True)
        self.stdout.write(f'\n Featured Products: {featured_products.count()}')
        
        self.stdout.write('\n' + '='*60 + '\n')