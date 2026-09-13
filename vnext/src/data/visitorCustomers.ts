export type VisitorCustomerStatus = 'فعال' | 'نیازمند پیگیری' | 'جدید'

export type VisitorCustomer = {
  id: string
  name: string
  owner: string
  code: string
  phone: string
  mobile: string
  area: string
  address: string
  route: string
  distance: string
  lastOrder: string
  lastVisit: string
  status: VisitorCustomerStatus
  total: string
  visits: string
  orders: string
  balance: string
  openInvoices: string
  openInvoiceAmount: string
  returnedCheque: string
  availableCredit: string
  location: string
}

export const visitorCustomers: VisitorCustomer[] = [
  {
    id: '1',
    name: 'سوپر مارکت رضایی',
    owner: 'آقای رضایی',
    code: 'C-10432',
    phone: '۰۲۶-۳۲۵۴ ۸۸۱۰',
    mobile: '۰۹۱۲ ۲۳۴ ۷۸۹۱',
    area: 'گوهردشت',
    address: 'گوهردشت، خیابان اصلی، نبش دوازدهم',
    route: 'مسیر ۳ · کرج غربی',
    distance: '۱.۲ km',
    lastOrder: 'امروز',
    lastVisit: '۱۰:۳۰',
    status: 'فعال',
    total: '۴۵.۲ م',
    visits: '۱۸',
    orders: '۱۴',
    balance: '۱۲.۸۵ م',
    openInvoices: '۳',
    openInvoiceAmount: '۸.۴ م',
    returnedCheque: '۰',
    availableCredit: '۳۲.۰ م',
    location: 'ثبت‌شده · دقت ۱۲ متر',
  },
  {
    id: '2',
    name: 'داروخانه نادری',
    owner: 'خانم نادری',
    code: 'C-10805',
    phone: '۰۲۶-۳۲۲۸ ۴۷۱۰',
    mobile: '۰۹۱۲ ۷۸۰ ۳۴۱۱',
    area: 'رجایی‌شهر',
    address: 'رجایی‌شهر، بلوار اصلی، پلاک ۷۸',
    route: 'مسیر ۳ · کرج غربی',
    distance: '۲.۴ km',
    lastOrder: 'دیروز',
    lastVisit: '۱۲:۰۰',
    status: 'فعال',
    total: '۲۸.۷ م',
    visits: '۱۲',
    orders: '۹',
    balance: '۶.۲ م',
    openInvoices: '۲',
    openInvoiceAmount: '۴.۱ م',
    returnedCheque: '۰',
    availableCredit: '۱۸.۵ م',
    location: 'ثبت‌شده · دقت ۱۸ متر',
  },
  {
    id: '3',
    name: 'فروشگاه سعیدی',
    owner: 'آقای سعیدی',
    code: 'C-11016',
    phone: '۰۲۶-۳۲۵۱ ۲۲۱۴',
    mobile: '۰۹۱۲ ۵۶۱ ۴۲۹۰',
    area: 'عظیمیه',
    address: 'عظیمیه، میدان اسبی، خیابان سرو',
    route: 'مسیر ۳ · کرج غربی',
    distance: '۰.۸ km',
    lastOrder: '۵ روز پیش',
    lastVisit: '۱۴:۱۵',
    status: 'نیازمند پیگیری',
    total: '۱۲.۴ م',
    visits: '۲۱',
    orders: '۱۵',
    balance: '۱۹.۴ م',
    openInvoices: '۴',
    openInvoiceAmount: '۱۲.۲ م',
    returnedCheque: '۱',
    availableCredit: '۸.۰ م',
    location: 'ثبت‌شده · دقت ۹ متر',
  },
  {
    id: '4',
    name: 'فروشگاه نیکان',
    owner: 'خانم احمدی',
    code: 'C-11308',
    phone: '۰۲۶-۳۲۲۵ ۱۸۳۰',
    mobile: '۰۹۱۰ ۲۲۸ ۶۶۱۲',
    area: 'جهانشهر',
    address: 'جهانشهر، بلوار جمهوری، نبش یاس',
    route: 'مسیر ۳ · کرج غربی',
    distance: '۳.۱ km',
    lastOrder: '—',
    lastVisit: 'ثبت نشده',
    status: 'جدید',
    total: '۰',
    visits: '۰',
    orders: '۰',
    balance: '۰',
    openInvoices: '۰',
    openInvoiceAmount: '۰',
    returnedCheque: '۰',
    availableCredit: '۱۵.۰ م',
    location: 'ثبت‌شده · دقت ۲۱ متر',
  },
  {
    id: '5',
    name: 'سوپر گلستان',
    owner: 'آقای گلستانی',
    code: 'C-11742',
    phone: '۰۲۶-۳۲۵۶ ۹۹۰۱',
    mobile: '۰۹۱۲ ۳۳۴ ۸۲۸۲',
    area: 'عظیمیه',
    address: 'عظیمیه، بلوار شریعتی، پلاک ۱۱۲',
    route: 'مسیر ۳ · کرج غربی',
    distance: '—',
    lastOrder: '۲ هفته پیش',
    lastVisit: 'ثبت نشده',
    status: 'نیازمند پیگیری',
    total: '۸.۹ م',
    visits: '۷',
    orders: '۵',
    balance: '۳.۱ م',
    openInvoices: '۱',
    openInvoiceAmount: '۲.۲ م',
    returnedCheque: '۰',
    availableCredit: '۱۰.۰ م',
    location: 'موقعیت ثبت نشده',
  },
]

export function getVisitorCustomer(customerId: string) {
  return visitorCustomers.find((customer) => customer.id === customerId) ?? visitorCustomers[0]!
}
