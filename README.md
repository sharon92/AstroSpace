# 🌌 AstroSpace

**AstroSpace** is a web application designed to host, organize, and showcase your astrophotography collection. 🔭 Sort celestial objects in timeline views, automatic annotation for your images (Plate Solving) and create a stunning digital observatory of your cosmic captures. ✨

Perfect for amateur astronomers, astrophotographers, and stargazers who want to organize their night sky adventures! 🌟

check out my Instance at:

[www.astro.space-js.de](https://astro.space-js.de/)
---

## 🚀 Key Features

- 🔐 **Secure User Authentication** - Protected access with customizable user limits
- 🎨 **Modern Tailwind CSS Interface** - Sleek, responsive design that looks professional
- 🌙 **Dark & Light Mode Support** - Perfect for both day and night viewing sessions
- 🗂️ **Dynamic Content Management** - Seamlessly handle static and dynamic astrophotography content
- 🧩 **Modular Architecture** - Clean, maintainable structure with reusable utilities and templates
- 🐳 **Docker Ready** - Containerized deployment for hassle-free setup
- ✍️ **Post Creation & Editing** - Document your observations and share your astrophotography journey
- 📊 **PHD2 Log Integration** - Upload and analyze your autoguiding logs for better tracking performance
- 🔍 **Plate Solving** - Automatically identify celestial objects and coordinates in your images
- 📱 **Responsive Design** - Access your collection from any device

---

## 📸 Screenshots

### 🖼️ Image Gallery with Detailed Information Tabs
Organize your astrophotography with rich metadata and detailed viewing options:

![Image Gallery Interface](https://github.com/user-attachments/assets/3fa18c68-780e-48a9-8121-763af082daba)

![Detailed Image View](https://github.com/user-attachments/assets/76b01b0f-763b-46b8-ba72-853b3e469c98)

![Image Information Panel](https://github.com/user-attachments/assets/34944a68-2bbb-42c5-b010-98812281b3ad)

### 📊 PHD2 Log Analysis
Upload and analyze your autoguiding performance:

![PHD2 Log Upload](https://github.com/user-attachments/assets/4f3ae6a4-5db6-4883-b88f-eaf6d5716b23)

### 🔐 User Authentication System
Secure login with configurable user limits (set `MAX_USERS` environment variable):

![User Login Interface](https://github.com/user-attachments/assets/85d07964-c1c6-491a-8496-f32870090984)

### ✍️ Content Creation
Create and share your astrophotography posts:

![Post Creation Interface](https://github.com/user-attachments/assets/0c164112-6a41-4e9c-9433-9d2c69673342)

---

## 📌 Upcoming Features

- 🛠️ **Equipment Inventory System** - Track your telescopes, cameras, filters, and accessories
- 📝 **Advanced Blogging Platform** - Enhanced tools for documenting observations and techniques
- ☀️ **Solar Photography Support** - Extended functionality for solar observation and imaging
- 🌍 **Weather Integration** - Connect with weather APIs for observing conditions
- 📈 **Advanced Analytics** - Detailed statistics about your imaging sessions and equipment performance

---

## 🛠️ Getting Started

### 🔧 Prerequisites

Before you begin, ensure you have the following installed on your system:

- 🐍 **Python 3.10+** - The core runtime environment
- 📦 **pip** - Python package installer
- 🗄️ **PostgreSQL** - Database server (or another SQL-compatible database)
- 🐳 **Docker** - *(Optional)* For containerized deployment
- 🌐 **Astrometry.net Account** - For plate-solving functionality

### 🧪 Local Development Setup

Follow these steps to get AstroSpace running on your local machine:

```bash
# 📥 Clone the repository
git clone https://github.com/sharon92/AstroSpace.git
cd AstroSpace

# 🔧 Set up a Python virtual environment
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate

# 📦 Install required dependencies
pip install -r requirements.txt

# ⚙️ Create configuration file
# Create a file at: instance/config.py
# Add the following configuration variables:
```

#### 📝 Configuration Template

Create `instance/config.py` with the following settings:

```python
# 🔐 Security Configuration
SECRET_KEY = 'your-super-secret-key-here'  # ⚠️ Change this in production!

# 🗄️ Database Configuration
DB_NAME = 'astrospace_db'
DB_USER = 'your_username'
DB_PASSWORD = 'your_secure_password'
DB_HOST = 'localhost'  # Or your database hostname
DB_PORT = 5432

# 🌟 Astrometry.net API Configuration
# Go to https://nova.astrometry.net and sign in to get your API key
ASTROMETRY_API_KEY = "your_astrometry_api_key_here"

# 👥 User Management
MAX_USERS = 5  # Set maximum number of registered users

# 🏷️ Site Branding
TITLE = "My AstroSpace Observatory"  # Customize your site name
```

```bash
# 🚀 Initialize the Database
flask --app AstroSpace init-db

# 🚀 Launch the application
flask --app AstroSpace run
```

Your AstroSpace instance will be available at `http://localhost:5000` 🌐

---

## 🤝 Contributing

We welcome contributions from the astrophotography community! 🌟

### Ways to Contribute:
- 🐛 **Bug Reports** - Found an issue? Let us know!
- 💡 **Feature Requests** - Have ideas for new functionality?
- 🔧 **Code Contributions** - Submit pull requests with improvements
- 📚 **Documentation** - Help improve our guides and documentation
- 🧪 **Testing** - Help test new features and report feedback

Feel free to:
- 📝 Open an issue for bugs or feature requests
- 🔀 Submit a pull request with your improvements
- 💬 Join discussions about the project's future

---

## 📝 License

This project is licensed under the **GNU GPL-3.0 License** 📄

This means you're free to use, modify, and distribute AstroSpace, but any modifications must also be open source under the same license. Perfect for keeping the astrophotography community's tools open and accessible! 🌍

---

## 📬 Get in Touch

Have questions, suggestions, or just want to share your amazing astrophotography results? Reach out!

- 📧 **Email:** [sharonshaji92@outlook.com](mailto:sharonshaji92@outlook.com)
- 🐙 **GitHub:** [https://github.com/sharon92](https://github.com/sharon92)
- ⭐ **Star this repo** if you find AstroSpace useful!

---

<div align="center">

**Made with ❤️ for the astrophotography community** 🌌

*Clear skies and happy imaging!* ✨🔭

</div>
