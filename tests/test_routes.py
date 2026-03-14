def test_home_route_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Latest Blogs" in response.data


def test_blog_index_route_renders(client):
    response = client.get("/blogs")
    assert response.status_code == 200
    assert b"First Light" in response.data


def test_blog_detail_route_renders(client):
    response = client.get("/blogs/first-light")
    assert response.status_code == 200
    assert b"Hello world" in response.data
