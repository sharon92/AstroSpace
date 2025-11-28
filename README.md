# 🌌 AstroSpace

**AstroSpace** is a web application designed to host, organize, and showcase your astrophotography collection, its basically your personal Astrobin/Instagram. 🔭 Sort celestial objects in timeline views, automatic annotation for your images (via Plate Solving), compare the size of your DSO with moon scale, explore the objects inside your DSO with Plotly graphs and much more! ✨

Perfect for amateur astronomers, astrophotographers, and stargazers who want to organize their night sky adventures and create their own personal space for Astro Stuff! 🌟

check out my Instance at:

[www.astro.space-js.de](https://astro.space-js.de/)
---

## 🚀 Key Features

- 🔐 **Secure User Authentication** – Protected access with customizable user limits  
- 🎨 **Modern Tailwind CSS Interface** – Sleek, responsive design that looks professional  
- 🌙 **Dark & Light Mode Support** – Perfect for both day and night viewing sessions  
- 🗂️ **Dynamic Content Management** – Seamlessly handle static and dynamic astrophotography content  
- 🧩 **Modular Architecture** – Clean, maintainable structure with reusable utilities and templates  
- 🐳 **Docker Ready** – Containerized deployment for hassle-free setup  
- ✍️ **Post Creation & Editing** – Document your observations and share your astrophotography journey  
- 📊 **PHD2 Log Integration** – Upload and analyze your autoguiding logs for better tracking performance  
- 🔍 **Plate Solving** – Automatically identify celestial objects and coordinates in your images  
- 📱 **Responsive Design** – Access your collection from any device  
- 🌕 **Moon Scale for DSO Frames** – Visualize the scale of deep sky objects in comparison to the Moon  
- 🗺️ **Equatorial Grid Overlay** – Overlay celestial coordinate grids for precise orientation  
- 🔗 **Shareable Links with Tabular Acquisition Details** – Easily share your captures along with structured metadata  
- 📈 **Explore DSO Contents with Plotly Graphs** – Interactively visualize SIMBAD and VizieR catalog queries. Plots a Hertzsprung Russel Diagram by default.
- 🛠️ **Equipment Inventory System** - Track your telescopes, cameras, filters, and accessories

---

## 📸 Screenshots

### 🖼️ Image Gallery with Detailed Information Tabs
Organize your astrophotography with rich metadata and detailed viewing options:

<img width="1410" height="1023" alt="image" src="https://github.com/user-attachments/assets/0a36167c-b738-4b41-96fa-1912d092af63" />

### Details

<img width="824" height="541" alt="image" src="https://github.com/user-attachments/assets/d7a16145-bae8-40a7-a814-edd6833e8a32" /> 
<img width="820" height="643" alt="image" src="https://github.com/user-attachments/assets/1f9241f4-a90a-4054-b571-1e0de79e608e" />
<img width="825" height="745" alt="image" src="https://github.com/user-attachments/assets/d2fc8000-c606-43c7-8414-859faae2372b" />

### 📊 PHD2 Log Analysis
Upload and analyze your autoguiding performance:

<img width="1220" height="1170" alt="image" src="https://github.com/user-attachments/assets/c92e1fbd-af4f-4765-a50e-337d1e0b77f9" />


### 🔐 User Authentication System
Secure login with configurable user limits (set `MAX_USERS` environment variable):

![User Login Interface](https://github.com/user-attachments/assets/85d07964-c1c6-491a-8496-f32870090984)

### ✍️ Content Creation
Create and share your astrophotography posts:

![Post Creation Interface](https://github.com/user-attachments/assets/0c164112-6a41-4e9c-9433-9d2c69673342)

---

## 📌 Upcoming Features

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

#### 📝 Configuration Template

Create `config.py` with the following settings:

```python
# 🔐 Security Configuration
SECRET_KEY = 'your-super-secret-key-here'  # ⚠️ Change this in production!

# 🗄️ Database Configuration
DB_NAME = 'astrospace_db'
DB_USER = 'your_username'
DB_PASSWORD = 'your_secure_password'
DB_HOST = 'localhost'  # Or your database hostname
DB_PORT = 5432

# 👥 User Management
MAX_USERS = 5  # Set maximum number of registered users

# 🏷️ Site Branding
TITLE = "My AstroSpace Observatory"  # Customize your site name can be changed later in settings

# Upload Path - uploaded jpegs and phd logs will be saved here
UPLOAD_PATH = "absolute/path/to/uploads
```

### 🧪 Local Setup
Follow these steps to get AstroSpace running on your local machine:

```bash
# 🔧 Set up a Python virtual environment
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate

# 📦 Install astrospace package
pip install astrospace

set ASTROSPACE_SETTINGS=path/to/config.py
flask --app AstroSpace run

#follow the link in the console to access your website
```

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

```

```bash
# 🚀 Launch the application
set ASTROSPACE_SETTINGS=path/to/config.py
flask --app AstroSpace run
```

Your AstroSpace instance will be available at `http://localhost:5000` 🌐

#### Docker Container

```bash
docker pull sharonshaji92/astrospace:latest
docker run \
  -d \
  --name='Your_Container_Name' \
  -e 'SECRET_KEY'='your_super_secret_key' \
  -e 'DB_NAME'='astrodb' \
  -e 'DB_USER'='test' \
  -e 'DB_PASSWORD'='123123' \
  -e 'DB_PORT'='8080' \
  -e 'TITLE'='Your_Website_Name' \
  -e 'MAX_USERS'='1' \
  -e 'DB_HOST'='0.0.0.0' \
  -e 'UPLOAD_PATH' = '/uploads' \
  -p '9000:9000/tcp' \
  -v '/path/on/server/to/mount/to/the/app':'/uploads' \
  sharonshaji92/astrospace:latest

```
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
