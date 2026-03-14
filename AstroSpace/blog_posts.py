import os

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for, current_app

from AstroSpace.auth import login_required
from AstroSpace.repositories.blog_posts import (
    delete_blog,
    get_blog_by_id,
    get_blog_by_slug,
    list_blogs,
    save_blog,
)
from AstroSpace.services.content import sanitize_rich_text
from AstroSpace.services.uploads import allowed_file, save_user_upload
from AstroSpace.utils.blog_form import BlogForm
from AstroSpace.utils.utils import ALLOWED_IMG_EXTENSIONS, resize_image


bp = Blueprint("blog_posts", __name__, url_prefix="/blogs")


def _store_blog_image(image_storage, user_id):
    if not image_storage or not image_storage.filename:
        return "", ""

    if not allowed_file(image_storage.filename, ALLOWED_IMG_EXTENSIONS):
        return "", ""

    stored_image = save_user_upload(image_storage, current_app.config["UPLOAD_PATH"], user_id)
    root, _ = os.path.splitext(stored_image.absolute_path)
    thumbnail_path = root + "_thumbnail.jpg"
    resize_image(stored_image.absolute_path, thumbnail_path)
    return (
        stored_image.public_path,
        f"{user_id}/{os.path.basename(thumbnail_path)}",
    )


@bp.route("")
def blog_index():
    blogs = list_blogs()
    return render_template("blog_list.html", blogs=blogs, WebName=current_app.config["TITLE"])


@bp.route("/<string:slug>")
def blog_detail(slug):
    blog = get_blog_by_slug(slug)
    if not blog:
        abort(404)
    return render_template("blog_detail.html", blog=blog, WebName=current_app.config["TITLE"])


@bp.route("/new", methods=("GET", "POST"))
@login_required
def new_blog():
    form = BlogForm()
    if form.validate_on_submit():
        image_path, image_thumbnail = _store_blog_image(form.image.data, g.user["id"])
        blog = save_blog(
            title=form.title.data,
            excerpt=sanitize_rich_text(form.excerpt.data),
            content_html=sanitize_rich_text(request.form.get("content")),
            author=g.user["username"],
            image_path=image_path,
            image_thumbnail=image_thumbnail,
        )
        flash("Blog post created successfully!")
        return redirect(url_for("blog_posts.blog_detail", slug=blog["slug"]))

    return render_template("create_blog.html", form=form, blog=None, WebName=current_app.config["TITLE"])


@bp.route("/<int:blog_id>/edit", methods=("GET", "POST"))
@login_required
def edit_blog(blog_id):
    blog = get_blog_by_id(blog_id)
    if not blog:
        abort(404)

    form = BlogForm(data={"title": blog["title"], "excerpt": blog.get("excerpt", "")})
    if form.validate_on_submit():
        image_path = blog.get("image_path", "")
        image_thumbnail = blog.get("image_thumbnail", "")
        if form.image.data and form.image.data.filename:
            image_path, image_thumbnail = _store_blog_image(form.image.data, g.user["id"])

        saved_blog = save_blog(
            blog_id=blog_id,
            title=form.title.data,
            excerpt=sanitize_rich_text(form.excerpt.data),
            content_html=sanitize_rich_text(request.form.get("content")),
            author=blog["author"],
            image_path=image_path,
            image_thumbnail=image_thumbnail,
        )
        flash("Blog post updated successfully!")
        return redirect(url_for("blog_posts.blog_detail", slug=saved_blog["slug"]))

    return render_template("create_blog.html", form=form, blog=blog, WebName=current_app.config["TITLE"])


@bp.route("/<int:blog_id>/delete", methods=("POST",))
@login_required
def remove_blog(blog_id):
    blog = get_blog_by_id(blog_id)
    if not blog:
        abort(404)

    delete_blog(blog_id)
    flash("Blog post deleted.")
    return redirect(url_for("blog_posts.blog_index"))
