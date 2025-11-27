# Nexus E-commerce Backend

A comprehensive Django REST Framework backend for an e-commerce platform featuring user authentication, product catalog management, review systems, and advanced security features.

## Project Overview

Nexus is a production-ready e-commerce backend built with Django and Django REST Framework. The platform provides essential e-commerce functionality including user management, product catalog operations, hierarchical category structures, and automated email notifications. The system is designed for scalability and performance with built-in caching mechanisms and asynchronous task processing.

## Key Features

### Authentication System

The authentication module provides complete user management capabilities with email-based registration and login. Users receive one-time password codes via email for account verification and password resets. The system tracks all login attempts with geolocation data to detect suspicious activity. Account security features include temporary lockouts after multiple failed login attempts and alerts for unusual login locations. Social authentication is supported for Google OAuth integration.

### Product Catalog

The product catalog supports unlimited hierarchical categories using modified preorder tree traversal for efficient queries. Products can be organized by brands and include multiple images with primary image designation. Each product supports flexible specifications stored as JSON, multiple currency options, discount pricing, and stock management with low-stock alerts. The system automatically tracks product view counts for analytics.

### Review System

Customers can leave product reviews with ratings from one to five stars. Each review includes a title and detailed comment. Reviews require administrative approval before display and can be marked as verified purchases. The system prevents duplicate reviews from the same user for a product.

### Performance Optimization

The platform implements Redis-based caching for product lists, product details, category trees, and brand lists. Cache invalidation occurs automatically when data changes through Celery tasks triggered by Django signals. This ensures users always see current information while maintaining fast response times.

### Email Notifications

All email operations process asynchronously through Celery workers to prevent blocking user requests. The system sends verification emails for new registrations, password reset codes, and security alerts for suspicious activity. Email tasks automatically retry on failure with exponential backoff.

### Security Features

User passwords undergo validation and secure hashing. JWT tokens manage authentication with automatic refresh and blacklisting capabilities. The system monitors login patterns to detect unusual activity such as multiple failed attempts or logins from new geographic locations. Rate limiting protects API endpoints from abuse.

## Technology Stack

The backend uses Django 5.2.8 as the web framework with Django REST Framework 3.16.1 for API development. PostgreSQL serves as the primary database while Redis 8.4 handles caching and message brokering. Celery 5.5.3 manages asynchronous tasks. Additional libraries include django-mptt for hierarchical categories, djangorestframework-simplejwt for JWT authentication, and drf-yasg for automatic API documentation.

## System Requirements

The application requires Python 3.12 or higher, PostgreSQL 15 or higher, and Redis 8.4 or higher. Docker and Docker Compose are needed for containerized deployment.

## Installation and Setup

### Environment Configuration

Begin by copying the environment template file to create your configuration:

```bash
cp .env.example .env
```

Edit the .env file to configure your environment variables. Generate a secure Django secret key using the following command:

```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

Set your database credentials, Redis connection strings, and email server details. For Gmail, you must create an App Password rather than using your regular password. Configure cache timeout values based on your performance requirements.

### Docker Deployment

Build and start all services using Docker Compose:

```bash
docker-compose up --build
```

This command starts four containers: the Django web application on port 8000, PostgreSQL database on port 5432, Redis cache on port 6379, and a Celery worker for background tasks.

### Database Migration

Once the containers are running, apply database migrations to create all necessary tables:

```bash
docker-compose exec web python manage.py migrate
```

### Administrative Access

Create a superuser account to access the Django admin panel:

```bash
docker-compose exec web python manage.py createsuperuser
```

Follow the prompts to set your administrator email and password.

## API Documentation

The API uses standard REST conventions with JSON for request and response bodies. Authentication requires JWT tokens passed in the Authorization header as Bearer tokens.

### Authentication Endpoints

User registration occurs at POST /api/auth/register/ with email, password, password confirmation, first name, and last name in the request body. The system responds with a success message and sends a verification code to the provided email.

Email verification uses POST /api/auth/verify-email/ with the email and six-digit OTP code. Successful verification enables account login.

Login requests go to POST /api/auth/login/ with email and password. The response includes access and refresh JWT tokens along with user information.

Token refresh occurs at POST /api/auth/token/refresh/ by providing the refresh token to receive a new access token.

Logout requests use POST /api/auth/logout/ with the refresh token to blacklist it and prevent further use.

Password reset requests start at POST /api/auth/password-reset/ with just the email address. The system sends a reset code to the email if the account exists.

Password reset confirmation uses POST /api/auth/password-reset/confirm/ with the email, OTP code, new password, and password confirmation.

### Product Catalog Endpoints

Category listings are available at GET /api/catalog/categories/ returning the complete hierarchical category tree. Individual categories can be retrieved at GET /api/catalog/categories/{slug}/.

Brand information is accessible at GET /api/catalog/brands/ for all active brands or GET /api/catalog/brands/{id}/ for specific brands.

Product listings support filtering, searching, and pagination at GET /api/catalog/products/. Query parameters include min_price and max_price for price ranges, category and brand for filtering, in_stock for availability, search for text queries, and ordering for sort options like price, -price, created_at, or name.

Individual product details are at GET /api/catalog/products/{slug}/ returning complete information including images, specifications, reviews, and ratings.

Product creation requires staff authentication at POST /api/catalog/products/ with product details in the request body. Updates use PUT or PATCH at /api/catalog/products/{slug}/ and deletion uses DELETE at the same endpoint.

Product reviews are listed at GET /api/catalog/products/{slug}/reviews/ and created at POST /api/catalog/products/{slug}/reviews/ with authenticated users providing rating, title, and comment.

### User Profile Endpoints

Current user information is accessible at GET /api/auth/me/ for authenticated users. Profile updates use PUT or PATCH at the same endpoint.

Login history retrieves the last fifty login attempts at GET /api/auth/login-history/ showing IP addresses, locations, and timestamps.

Security claims list unresolved security alerts at GET /api/auth/security-claims/ including unusual locations and account lockouts.

## Interactive API Documentation

Swagger UI provides an interactive interface for exploring and testing endpoints at http://localhost:8000/swagger/. ReDoc offers alternative documentation at http://localhost:8000/redoc/.

## Administrative Interface

The Django admin panel is accessible at http://localhost:8000/admin/ after logging in with your superuser credentials. The interface provides comprehensive management for users, categories, brands, products, images, and reviews with custom actions and visual enhancements.

## Architecture Overview

### Application Structure

The project follows Django's app-based architecture with two main applications. The authentication app handles user management, login tracking, security monitoring, and email notifications. The product catalog app manages categories, brands, products, images, and reviews.

### Caching Strategy

Redis maintains three separate databases for different caching purposes. Database one serves as the default cache, database two handles product catalog caching with keys prefixed by "catalog", and database three manages authentication caching for OTP storage and token blacklisting with keys prefixed by "auth".

The caching system uses intelligent key generation to prevent collision. Product lists generate unique keys based on the complete query string including filters and pagination parameters. Product details use simple product ID keys. Category trees and brand lists use versioned keys for easy invalidation.

Automatic cache invalidation occurs through Django signals connected in the ready method of each app configuration. When products or categories are saved or deleted, Celery tasks execute to clear relevant caches ensuring data consistency.

### Asynchronous Task Processing

Celery workers handle three categories of background tasks. Email tasks send verification codes, password reset instructions, and security alerts with automatic retry on failure. Cache invalidation tasks clear product and category caches after database changes. Future task categories might include image processing, report generation, and inventory synchronization.

### Database Design

PostgreSQL stores all application data with careful index optimization. The User model extends Django's AbstractBaseUser with email as the username field, UUID primary keys, and optional social authentication fields. LoginHistory tracks every authentication attempt with IP addresses, user agents, and geolocation data. SecurityClaim records security events requiring user attention.

Categories use modified preorder tree traversal through django-mptt for efficient hierarchical queries. Products link to categories and brands with comprehensive fields for pricing, inventory, and specifications. ProductImage supports multiple images per product with primary designation. ProductReview implements the one review per user per product constraint.

## Development Guidelines

### Code Organization

Service classes encapsulate business logic separate from views. OTPService manages one-time password generation and verification. EmailService coordinates asynchronous email sending. GeoLocationService retrieves geographic data from IP addresses. LoginTrackingService monitors authentication patterns. TokenBlacklistService manages JWT token invalidation.

Views remain thin, delegating work to serializers and services. Serializers handle data validation and transformation. Models contain only database-related logic and computed properties.

### Testing Approach

The project structure supports comprehensive testing. For asynchronous email tasks, enable Celery eager mode in test settings to execute tasks synchronously. Mock external services like geolocation APIs to avoid dependencies on external systems. Test authentication flows including registration, verification, login, and password reset. Validate product filtering, searching, and pagination. Verify cache invalidation triggers correctly. Test rate limiting and security features.

### Logging Configuration

The logging system writes to both console and files. The console handler displays all logs during development. The file handler saves application logs to the logs directory in production. Separate loggers track Django framework events, application-specific events, authentication operations, product catalog operations, and Celery task execution.

## Security Considerations

### Authentication Security

Passwords undergo validation through Django's password validators checking for similarity to user attributes, minimum length requirements, common password detection, and purely numeric passwords. All passwords are hashed using Django's PBKDF2 algorithm before storage.

OTP codes generate using Python's secrets module for cryptographic security rather than the standard random module. Codes expire after ten minutes and are stored in Redis with automatic cleanup.

JWT tokens have a one-hour lifetime for access tokens and seven-day lifetime for refresh tokens. Refresh tokens rotate on use with old tokens blacklisted. Token blacklisting stores JWT IDs in Redis with automatic expiration matching token lifetime.

### API Security

Rate limiting restricts anonymous users to one hundred requests per hour and authenticated users to one thousand requests per hour. CORS configuration should be adjusted before production deployment to restrict allowed origins.

The CSRF protection middleware remains active for form-based requests. API endpoints primarily use JWT authentication which does not require CSRF tokens.

### Data Protection

User data including names and email addresses are never exposed unnecessarily. Login history and security claims are only visible to the account owner. Admin access requires staff privileges verified through Django's permission system.

## Performance Optimization

### Database Optimization

Query optimization uses select_related for foreign key relationships and prefetch_related for many-to-many and reverse foreign key relationships. Database indexes cover frequently queried fields including email addresses, slugs, product status, pricing, and category hierarchy fields.

### Caching Strategy

Cache timeouts balance freshness with performance. Category trees cache for one hour since categories rarely change. Product lists cache for thirty minutes as product availability and pricing update regularly. Product details cache for one hour as individual products change less frequently than list views.

Cache invalidation occurs immediately after database changes rather than waiting for expiration. This ensures consistency while maintaining cache benefits.

### Asynchronous Processing

Email sending moves to background workers preventing request blocking. The typical registration request completes in under one hundred milliseconds while email delivery occurs separately over one to three seconds.

Database-intensive operations like geolocation lookups occur asynchronously during login tracking. Users receive immediate login confirmation while location data processes in the background.

## Deployment Considerations

### Production Configuration

Disable debug mode by setting DEBUG to False in environment variables. Configure allowed hosts to include your production domain names. Generate a new secret key unique to the production environment. Configure secure cookie settings including SECURE_SSL_REDIRECT, SESSION_COOKIE_SECURE, and CSRF_COOKIE_SECURE.

### Database Configuration

Use connection pooling to manage database connections efficiently. Configure regular backups with point-in-time recovery capability. Set up replication for high availability. Monitor query performance and add indexes as needed.

### Static File Serving

Collect static files using Django's collectstatic command. Serve static files through a CDN or web server like Nginx rather than Django. Configure media file uploads to cloud storage like AWS S3 for scalability.

### Monitoring and Logging

Implement application monitoring using services like Sentry for error tracking. Set up log aggregation using ELK stack or CloudWatch. Monitor Celery task execution and queue lengths. Track API endpoint response times and error rates. Configure alerts for critical events like high error rates or database connection failures.

## Support and Contribution

### Getting Help

Consult the interactive API documentation at the Swagger endpoint for detailed endpoint specifications. Review the Django admin interface for data management capabilities. Check Celery worker logs for task execution details. Examine application logs in the logs directory for debugging information.

### Project Status

The project is production-ready with all core features implemented and tested. The authentication system provides comprehensive user management. The product catalog supports complex hierarchical organization. The caching system ensures optimal performance. The asynchronous task processing enables scalability.

## License

This project is released under the MIT License, allowing free use, modification, and distribution with attribution.