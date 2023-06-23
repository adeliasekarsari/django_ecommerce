from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.csrf import csrf_exempt
from django_ratelimit.decorators import ratelimit

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.utils import timezone
from django.views import generic
from paypal.standard.forms import PayPalPaymentsForm
from django.contrib.postgres.search import SearchQuery, SearchVector

from .forms import CheckoutForm, ContactForm, CommentForm
from .models import ProdukItem, OrderProdukItem, Order, AlamatPengiriman, Payment
from django.core.mail import send_mail, BadHeaderError
from django.http import HttpResponse

class HomeListView(generic.ListView):
    template_name = 'home.html'
    queryset = ProdukItem.objects.all()
    paginate_by = 8

class SearchView(generic.ListView):
    model = ProdukItem
    template_name = 'search.html'
    context_object_name = 'all_search_results'

    def get_queryset(self):
        result = super(SearchView, self).get_queryset()
        query = self.request.GET.get('search')
        if query:
            postresult = ProdukItem.objects.filter(nama_produk=query)
            result = postresult
        else:
            result = None
        return result

class SearchResultView(generic.ListView):
    model = ProdukItem
    template_name = 'search.html'
    context_object_name = 'all_search_results'
    def get_queryset(self):
        query = self.request.GET.get('search')
        object_list = ProdukItem.objects.annotate(
            search = SearchVector('nama_produk','kategori')
        ).filter(search=query)
        return object_list

class ProductDetailView(generic.DetailView):
    template_name = 'product_detail.html'
    queryset = ProdukItem.objects.all()
    
class ProductTView(generic.ListView):
    template_name = 'home.html'
    queryset = ProdukItem.objects.all().filter(kategori='T')
    paginate_by = 8

class ProductAView(generic.ListView):
    template_name = 'home.html'
    queryset = ProdukItem.objects.all()
    paginate_by = 8

class ProductBView(generic.ListView):
    template_name = 'home.html'
    queryset = ProdukItem.objects.all().filter(kategori='B')
    paginate_by = 8

class ProductOView(generic.ListView):
    template_name = 'home.html'
    queryset = ProdukItem.objects.all().filter(kategori='O')
    paginate_by = 8

class CheckoutView(LoginRequiredMixin, generic.FormView):
    def get(self, *args, **kwargs):
        form = CheckoutForm()
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if order.produk_items.count() == 0:
                messages.warning(self.request, 'No products in the cart')
                return redirect('toko:home-produk-list')
        except ObjectDoesNotExist:
            order = {}
            messages.warning(self.request, 'No products in the cart')
            return redirect('toko:home-produk-list')

        context = {
            'form': form,
            'keranjang': order,
        }
        template_name = 'checkout.html'
        return render(self.request, template_name, context)

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():
                alamat_1 = form.cleaned_data.get('alamat_1')
                alamat_2 = form.cleaned_data.get('alamat_2')
                negara = form.cleaned_data.get('negara')
                kode_pos = form.cleaned_data.get('kode_pos')
                opsi_pembayaran = form.cleaned_data.get('opsi_pembayaran')
                alamat_pengiriman = AlamatPengiriman(
                    user=self.request.user,
                    alamat_1=alamat_1,
                    alamat_2=alamat_2,
                    negara=negara,
                    kode_pos=kode_pos,
                )

                alamat_pengiriman.save()
                order.alamat_pengiriman = alamat_pengiriman
                order.save()
                if opsi_pembayaran == 'P':
                    return redirect('toko:payment', payment_method='paypal')
                else:
                    return redirect('toko:payment', payment_method='stripe')

            messages.warning(self.request, 'Gagal checkout')
            return redirect('toko:checkout')
        except ObjectDoesNotExist:
            messages.error(self.request, 'Tidak ada pesanan yang aktif')
            return redirect('toko:order-summary')

#@login_required
class PaymentView(LoginRequiredMixin, generic.FormView):
    def get(self, *args, **kwargs):
        template_name = 'payment.html'
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            
            paypal_data = {
                'business': settings.PAYPAL_RECEIVER_EMAIL,
                'amount': order.get_total_harga_order,
                'item_name': f'Pembayaran belajanan order: {order.id}',
                'invoice': f'{order.id}-{timezone.now().timestamp()}' ,
                'currency_code': 'USD',
                'notify_url': self.request.build_absolute_uri(reverse('paypal-ipn')),
                'return_url': self.request.build_absolute_uri(reverse('toko:paypal-return')),
                'cancel_return': self.request.build_absolute_uri(reverse('toko:paypal-cancel')),
            }
        
            qPath = self.request.get_full_path()
            isPaypal = 'paypal' in qPath
        
            form = PayPalPaymentsForm(initial=paypal_data)
            context = {
                'paypalform': form,
                'order': order,
                'is_paypal': isPaypal,
            }
            return render(self.request, template_name, context)

        except ObjectDoesNotExist:
            return redirect('toko:checkout')

#@login_required
class OrderSummaryView(LoginRequiredMixin, generic.TemplateView):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'keranjang': order
            }
            template_name = 'order_summary.html'
            return render(self.request, template_name, context)
        except ObjectDoesNotExist:
            messages.error(self.request, 'Tidak ada pesanan yang aktif')
            return redirect('/')
@login_required
def add_to_cart(request, slug):
    if request.user.is_authenticated:
        produk_item = get_object_or_404(ProdukItem, slug=slug)
        order_produk_item, _ = OrderProdukItem.objects.get_or_create(
            produk_item=produk_item,
            user=request.user,
            ordered=False
        )
        order_query = Order.objects.filter(user=request.user, ordered=False)
        if order_query.exists():
            order = order_query[0]
            if order.produk_items.filter(produk_item__slug=produk_item.slug).exists():
                order_produk_item.quantity += 1
                order_produk_item.save()
                pesan = f"ProdukItem sudah diupdate menjadi: { order_produk_item.quantity }"
                messages.info(request, pesan)
                return redirect('toko:produk-detail', slug = slug)
            else:
                order.produk_items.add(order_produk_item)
                messages.info(request, 'ProdukItem pilihanmu sudah ditambahkan')
                return redirect('toko:produk-detail', slug = slug)
        else:
            tanggal_order = timezone.now()
            order = Order.objects.create(user=request.user, tanggal_order=tanggal_order)
            order.produk_items.add(order_produk_item)
            messages.info(request, 'ProdukItem pilihanmu sudah ditambahkan')
            return redirect('toko:produk-detail', slug = slug)
    else:
        return redirect('/accounts/login')

@login_required
@ratelimit(key='user',rate='10/h')
def remove_from_cart(request, slug):
    if request.user.is_authenticated:
        produk_item = get_object_or_404(ProdukItem, slug=slug)
        order_query = Order.objects.filter(
            user=request.user, ordered=False
        )
        if order_query.exists():
            order = order_query[0]
            if order.produk_items.filter(produk_item__slug=produk_item.slug).exists():
                try: 
                    order_produk_item = OrderProdukItem.objects.filter(
                        produk_item=produk_item,
                        user=request.user,
                        ordered=False
                    )[0]
                    
                    order.produk_items.remove(order_produk_item)
                    order_produk_item.delete()

                    pesan = f"ProdukItem sudah dihapus"
                    messages.info(request, pesan)
                    return redirect('toko:produk-detail',slug = slug)
                except ObjectDoesNotExist:
                    print('Error: order ProdukItem sudah tidak ada')
            else:
                messages.info(request, 'ProdukItem tidak ada')
                return redirect('toko:produk-detail',slug = slug)
        else:
            messages.info(request, 'ProdukItem tidak ada order yang aktif')
            return redirect('toko:produk-detail',slug = slug)
    else:
        return redirect('/accounts/login')

@csrf_exempt
@login_required
@ratelimit(key='user',rate='10/h')
def paypal_return(request):
    if request.user.is_authenticated:
        try:
            print('paypal return', request)
            order = Order.objects.get(user=request.user, ordered=False)
            payment = Payment()
            payment.user=request.user
            payment.amount = order.get_total_harga_order()
            payment.payment_option = 'P' # paypal kalai 'S' stripe
            payment.charge_id = f'{order.id}-{timezone.now()}'
            payment.timestamp = timezone.now()
            payment.save()
            
            order_produk_item = OrderProdukItem.objects.filter(user=request.user,ordered=False)
            order_produk_item.update(ordered=True)
            
            order.payment = payment
            order.ordered = True
            order.save()

            messages.info(request, 'Pembayaran sudah diterima, terima kasih')
            return redirect('toko:home-produk-list')
        except ObjectDoesNotExist:
            messages.error(request, 'Periksa kembali pesananmu')
            return redirect('toko:order-summary')
    else:
        return redirect('/accounts/login')

@csrf_exempt
@login_required
@ratelimit(key='user',rate='10/h')
def paypal_cancel(request):
    messages.error(request, 'Pembayaran dibatalkan')
    return redirect('toko:order-summary')

@csrf_exempt
@login_required
@ratelimit(key='user',rate='10/h')
def contact_us(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            subject = "Website Inquiry" 
            body = {
                "name" : form.cleaned_data['name'],
                "email" : form.cleaned_data['email'],
                "subject" : form.cleaned_data['subject'],
                "message" : form.cleaned_data['message'], 
			}
            message = "\n".join(body.values())
            
            try:
                send_mail(subject, message, form.cleaned_data['email'], ['admin@example.com']) 
            except BadHeaderError:
                return HttpResponse('Invalid header found.')
            return redirect ("toko:success-message")
    form = ContactForm()
    
    return render(request, "contact.html", {'form':form})

def successView(request):
    return render(request, "message.html")




