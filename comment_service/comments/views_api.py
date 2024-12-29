from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework_jwt.utils import jwt_decode_handler
from comments.models import Comment, Like


def get_user_id(request):
    try:
        return int(jwt_decode_handler(request.headers["Authorization"][4:])["user_id"])
    except:
        return None


@api_view(['GET', 'POST'])
def manage_comments(request):
    if not get_user_id(request):
        return Response(status=status.HTTP_401_UNAUTHORIZED)
    if request.GET:
        return listing(request)
    return create(request)


def listing(request):
    user_id = get_user_id(request)
    product_id = request.GET["product"]

    try:
        page = int(request.GET["page"])
    except:
        page = 0
    try:
        size = int(request.GET["size"])
    except:
        size = 10

    comments = Comment.objects.filter(product_id=product_id, parent=None).order_by('-created_on')[page * size:(page + 1) * size]
    data = []

    for comment in comments:
        data.append({
            'id': comment.id,
            'created_on': comment.created_on,
            'user_id': comment.user_id,
            'product_id': comment.product_id,
            'email': comment.email,
            'text': comment.text,
            'likes': len(Like.objects.filter(comment_id=comment.id, dislike=False)),
            'dislikes': len(Like.objects.filter(comment_id=comment.id, dislike=True)),
            'liked': len(Like.objects.filter(user_id=user_id, comment_id=comment.id, dislike=False)) > 0,
            'disliked': len(Like.objects.filter(user_id=user_id, comment_id=comment.id, dislike=True)) > 0
        })

    return Response(data=data, status=status.HTTP_200_OK, content_type='application/json', headers={
        'Access-Control-Expose-Headers': 'First-Page, Last-Page',
        'First-Page': page == 0,
        'Last-Page': (page + 1) * size >= len(Comment.objects.filter(product_id=product_id, parent=None))
    })


def create(request):
    try:
        parent_id = request.data['parent_id']
    except:
        parent_id = None

    comment = Comment.objects.create(product_id=int(request.data['product_id']), text=request.data['text'], parent_id=parent_id)
    comment.user_id = get_user_id(request)
    comment.email = jwt_decode_handler(request.headers["Authorization"][4:])["email"]
    comment.save()
    return Response(status=status.HTTP_200_OK)


@api_view(['DELETE'])
def delete_comment(request, key):
    user_id = get_user_id(request)
    if not user_id:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
    try:
        comment = Comment.objects.get(id=key)
        if comment.user_id != user_id:
            return Response(status=status.HTTP_403_FORBIDDEN)
        comment.delete()
        return Response(status=status.HTTP_200_OK)
    except Comment.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def like(request, key):
    user_id = get_user_id(request)
    if not user_id:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
    try:
        disliked = request.GET['dislike'] == "true"
    except:
        disliked = False
    comment = Comment.objects.get(id=key)

    if not disliked:
        try:
            like = Like.objects.get(user_id=user_id, comment_id=comment.id, dislike=False)
            like.delete()
        except Like.DoesNotExist:
            Like.objects.create(user_id=user_id, comment=comment, dislike=False)
            try:
                dislike = Like.objects.get(user_id=user_id, comment_id=comment.id, dislike=True)
                dislike.delete()
            except Like.DoesNotExist:
                pass
    else:
        try:
            dislike = Like.objects.get(user_id=user_id, comment_id=comment.id, dislike=True)
            dislike.delete()
        except Like.DoesNotExist:
            Like.objects.create(user_id=user_id, comment=comment, dislike=True)
        try:
            like = Like.objects.get(user_id=user_id, comment_id=comment.id, dislike=False)
            like.delete()
        except Like.DoesNotExist:
            pass

    return Response(status=status.HTTP_200_OK)


@api_view(['GET'])
def replies(request, key):
    user_id = get_user_id(request)
    if not user_id:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
    comments = Comment.objects.filter(parent_id=key).order_by('-created_on')
    data = []

    for comment in comments:
        data.append({
            'id': comment.id,
            'created_on': comment.created_on,
            'user_id': comment.user_id,
            'email': comment.email,
            'product_id': comment.product_id,
            'text': comment.text,
            'likes': len(Like.objects.filter(comment_id=comment.id, dislike=False)),
            'dislikes': len(Like.objects.filter(comment_id=comment.id, dislike=True)),
            'liked': len(Like.objects.filter(user_id=user_id, comment_id=comment.id, dislike=False)) > 0,
            'disliked': len(Like.objects.filter(user_id=user_id, comment_id=comment.id, dislike=True)) > 0
        })

    return Response(status=status.HTTP_200_OK, data=data, content_type='application/json')


@api_view(['GET'])
def comments_statistic(_, start, end):
    if start >= end:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    result = []
    for i in range(start, end+1):
        result.append([
            i, len(Comment.objects.filter(created_on__year=i))
        ])
    return Response(status=status.HTTP_200_OK, data=result, content_type='application/json')


@api_view(['GET'])
def likes_statistic(_, start, end):
    if start >= end:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    result = []
    for i in range(start, end+1):
        result.append([
            i, len(Like.objects.filter(created_on__year=i, dislike=False))
        ])
    return Response(status=status.HTTP_200_OK, data=result, content_type='application/json')


@api_view(['GET'])
def dislikes_statistic(_, start, end):
    if start >= end:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    result = []
    for i in range(start, end+1):
        result.append([
            i, len(Like.objects.filter(created_on__year=i, dislike=True))
        ])
    return Response(status=status.HTTP_200_OK, data=result, content_type='application/json')
