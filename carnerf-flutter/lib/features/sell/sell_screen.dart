import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/api/api_client.dart';
import '../../core/api/listings_api.dart';
import '../../core/api/pipeline_api.dart';
import '../../core/api/predict_api.dart';
import '../../core/api/upload_api.dart';
import '../../core/constants/car_options.dart';
import '../../core/models/price_estimate.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/formatters/krw.dart';
import '../../shared/widgets/app_chip.dart';
import '../../shared/widgets/dark_card.dart';
import '../../shared/widgets/gold_button.dart';
import 'widgets/pipeline_stepper.dart';

const _steps = ['기본정보', '옵션', 'AI 시세', '가격', '사진', '3D 영상'];
const _brands = [
  '현대', '기아', '제네시스', '쉐보레', 'BMW', '벤츠', '아우디', '렉서스', '포르쉐'
];
const _fuels = ['가솔린', '디젤', 'LPG', '하이브리드', '전기'];
const _trans = ['자동', '수동'];
const _regions = [
  '서울', '경기', '인천', '부산', '대구', '대전', '광주', '울산'
];

class SellScreen extends ConsumerStatefulWidget {
  const SellScreen({super.key});

  @override
  ConsumerState<SellScreen> createState() => _SellScreenState();
}

class _SellScreenState extends ConsumerState<SellScreen> {
  int _step = 0;

  String _brand = '현대';
  final _model = TextEditingController();
  final _year = TextEditingController();
  final _trim = TextEditingController();
  final _mileage = TextEditingController();
  String _fuel = '가솔린';
  String _transmission = '자동';
  final _engineCc = TextEditingController();
  String _region = '서울';

  final Set<String> _options = {};

  final _title = TextEditingController();
  final _description = TextEditingController();
  final _price = TextEditingController();
  bool _negotiable = true;

  List<XFile> _images = [];
  XFile? _video;
  PipelineQuality _quality = PipelineQuality.standard;

  String? _jobId;
  PipelineStatus? _pipelineStatus;
  Timer? _pollTimer;

  bool _priceLoading = false;
  PriceEstimate? _priceEstimate;
  bool _submitLoading = false;

  void rebuild(VoidCallback fn) => setState(fn);

  @override
  void dispose() {
    _model.dispose();
    _year.dispose();
    _trim.dispose();
    _mileage.dispose();
    _engineCc.dispose();
    _title.dispose();
    _description.dispose();
    _price.dispose();
    _pollTimer?.cancel();
    super.dispose();
  }

  void _toast(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        backgroundColor: AppColors.surface,
        content: Text(msg, style: const TextStyle(color: AppColors.gold)),
      ),
    );
  }

  bool get _canNext {
    if (_step == 0) {
      return _model.text.isNotEmpty &&
          _year.text.isNotEmpty &&
          _mileage.text.isNotEmpty;
    }
    if (_step == 3) {
      final p = int.tryParse(_price.text);
      return p != null && p > 0;
    }
    return true;
  }

  Future<void> _pickImages() async {
    final picker = ImagePicker();
    final picked = await picker.pickMultiImage(limit: 10, imageQuality: 80);
    if (picked.isEmpty) return;
    setState(() {
      _images = [..._images, ...picked].take(10).toList();
    });
  }

  Future<void> _pickVideo() async {
    final picker = ImagePicker();
    final v = await picker.pickVideo(source: ImageSource.gallery);
    if (v == null) return;
    setState(() => _video = v);
  }

  Future<void> _runPricePrediction() async {
    final yr = int.tryParse(_year.text);
    final mi = int.tryParse(_mileage.text);
    if (yr == null || mi == null) {
      _toast('연식과 주행거리를 먼저 입력하세요');
      return;
    }
    setState(() => _priceLoading = true);
    try {
      final r = await ref.read(predictApiProvider).price(
            PricePredictBody(
              brand: _brand,
              model: _model.text,
              year: yr,
              mileage: mi,
              fuelType: _fuel,
              transmission: _transmission,
              engineCc: int.tryParse(_engineCc.text),
              region: _region,
            ),
          );
      if (!mounted) return;
      setState(() => _priceEstimate = r);
    } catch (e) {
      _toast(extractApiError(e));
    } finally {
      if (mounted) setState(() => _priceLoading = false);
    }
  }

  Future<void> _submit() async {
    setState(() => _submitLoading = true);
    try {
      List<String> imageUrls = [];
      if (_images.isNotEmpty) {
        final r = await ref.read(uploadApiProvider).images(
              _images.map((x) => x.path).toList(),
            );
        imageUrls = r.urls;
      }
      final yr = int.tryParse(_year.text) ?? DateTime.now().year;
      final mi = int.tryParse(_mileage.text) ?? 0;
      final pr = int.tryParse(_price.text) ?? 0;
      final fallbackTitle = '$yr $_brand ${_model.text}';

      final listing = await ref.read(listingsApiProvider).create({
        'brand': _brand,
        'model': _model.text,
        'year': yr,
        if (_trim.text.isNotEmpty) 'trim': _trim.text,
        'fuel_type': _fuel,
        'transmission': _transmission,
        'mileage': mi,
        if (_engineCc.text.isNotEmpty) 'engine_cc': int.parse(_engineCc.text),
        'region': _region,
        'title': _title.text.isEmpty ? fallbackTitle : _title.text,
        'description': _description.text,
        'price': pr,
        'is_negotiable': _negotiable,
        'image_urls': imageUrls,
        'options': _options.toList(),
      });

      if (_video != null) {
        final jobId = await ref.read(pipelineApiProvider).start(
              videoPath: _video!.path,
              vehicleId: listing.vehicle?.id,
              quality: _quality,
            );
        if (!mounted) return;
        setState(() => _jobId = jobId);
        _startPolling(jobId);
      }
      _toast('매물이 등록되었습니다');
    } catch (e) {
      _toast(extractApiError(e));
    } finally {
      if (mounted) setState(() => _submitLoading = false);
    }
  }

  void _startPolling(String jobId) {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(seconds: 3), (timer) async {
      try {
        final s = await ref.read(pipelineApiProvider).status(jobId);
        if (!mounted) {
          timer.cancel();
          return;
        }
        setState(() => _pipelineStatus = s);
        if (s.status == PipelinePhase.completed ||
            s.status == PipelinePhase.failed) {
          timer.cancel();
        }
      } catch (_) {
        // 잠시 후 재시도 — 폴링 유지
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.black,
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Padding(
              padding: EdgeInsets.fromLTRB(20, 12, 20, 4),
              child: Text(
                '내 차 팔기',
                style: TextStyle(
                  color: AppColors.white,
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 20),
              child: Text(
                '영상만 올리면 3D · AI 시세 · 결함 리포트 자동 생성',
                style: TextStyle(color: AppColors.muted, fontSize: 12),
              ),
            ),
            const SizedBox(height: 14),
            _StepIndicator(step: _step),
            const SizedBox(height: 14),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 120),
                child: _stepBody(),
              ),
            ),
            _BottomBar(
              step: _step,
              canNext: _canNext,
              onPrev: _step > 0 ? () => setState(() => _step--) : null,
              onNext: _canNext && _step < _steps.length - 1
                  ? () => setState(() => _step++)
                  : null,
            ),
          ],
        ),
      ),
    );
  }

  Widget _stepBody() {
    switch (_step) {
      case 0:
        return _BasicStep(this);
      case 1:
        return _OptionsStep(this);
      case 2:
        return _PriceAiStep(this);
      case 3:
        return _PricingStep(this);
      case 4:
        return _ImagesStep(this);
      case 5:
        return _VideoStep(this);
    }
    return const SizedBox.shrink();
  }
}

class _StepIndicator extends StatelessWidget {
  const _StepIndicator({required this.step});
  final int step;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Row(
        children: List.generate(_steps.length, (i) {
          final active = i <= step;
          return Expanded(
            child: Padding(
              padding: EdgeInsets.only(right: i == _steps.length - 1 ? 0 : 4),
              child: Column(
                children: [
                  Container(
                    height: 5,
                    decoration: BoxDecoration(
                      color: active
                          ? AppColors.gold
                          : Colors.white.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(999),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _steps[i],
                    style: TextStyle(
                      color: i == step ? AppColors.gold : AppColors.muted,
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
          );
        }),
      ),
    );
  }
}

class _BottomBar extends StatelessWidget {
  const _BottomBar({
    required this.step,
    required this.canNext,
    required this.onPrev,
    required this.onNext,
  });

  final int step;
  final bool canNext;
  final VoidCallback? onPrev;
  final VoidCallback? onNext;

  @override
  Widget build(BuildContext context) {
    final showNext = step < _steps.length - 1;
    return Container(
      padding: EdgeInsets.fromLTRB(
        20,
        10,
        20,
        MediaQuery.paddingOf(context).bottom + 12,
      ),
      decoration: const BoxDecoration(
        color: Color(0xFF0A0A0A),
        border: Border(top: BorderSide(color: AppColors.border)),
      ),
      child: Row(
        children: [
          if (onPrev != null)
            Expanded(
              child: OutlineGoldButton(
                label: '이전',
                icon: Icons.chevron_left,
                onPressed: onPrev,
              ),
            ),
          if (onPrev != null && showNext) const SizedBox(width: 10),
          if (showNext)
            Expanded(
              flex: 2,
              child: GoldButton(
                label: '다음',
                icon: Icons.chevron_right,
                onPressed: canNext ? onNext : null,
                expand: true,
              ),
            ),
        ],
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.child});
  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              color: AppColors.white,
              fontSize: 12,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          child,
        ],
      ),
    );
  }
}

class _ChipRow extends StatelessWidget {
  const _ChipRow({
    required this.items,
    required this.value,
    required this.onPick,
  });
  final List<String> items;
  final String value;
  final ValueChanged<String> onPick;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 36,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: items.length,
        separatorBuilder: (_, _) => const SizedBox(width: 8),
        itemBuilder: (_, i) => AppChip(
          label: items[i],
          selected: value == items[i],
          onTap: () => onPick(items[i]),
        ),
      ),
    );
  }
}

class _Field extends StatelessWidget {
  const _Field({
    required this.controller,
    required this.label,
    this.hint,
    this.keyboardType,
    this.maxLines,
  });

  final TextEditingController controller;
  final String label;
  final String? hint;
  final TextInputType? keyboardType;
  final int? maxLines;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(
              color: AppColors.white,
              fontSize: 12,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 6),
          TextField(
            controller: controller,
            keyboardType: keyboardType,
            maxLines: maxLines ?? 1,
            style: const TextStyle(color: AppColors.white),
            decoration: InputDecoration(
              hintText: hint,
              hintStyle: const TextStyle(color: AppColors.muted),
            ),
          ),
        ],
      ),
    );
  }
}

class _BasicStep extends StatelessWidget {
  const _BasicStep(this.s);
  final _SellScreenState s;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _Section(
          title: '브랜드',
          child: _ChipRow(
            items: _brands,
            value: s._brand,
            onPick: (v) => s.rebuild(() => s._brand = v),
          ),
        ),
        _Field(controller: s._model, label: '모델명', hint: '예: 그랜저 IG'),
        Row(
          children: [
            Expanded(
              child: _Field(
                controller: s._year,
                label: '연식',
                hint: '2022',
                keyboardType: TextInputType.number,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _Field(
                controller: s._mileage,
                label: '주행거리 (km)',
                hint: '32000',
                keyboardType: TextInputType.number,
              ),
            ),
          ],
        ),
        _Field(controller: s._trim, label: '트림 (선택)'),
        _Field(
          controller: s._engineCc,
          label: '배기량 (cc, 선택)',
          keyboardType: TextInputType.number,
        ),
        _Section(
          title: '연료',
          child: _ChipRow(
            items: _fuels,
            value: s._fuel,
            onPick: (v) => s.rebuild(() => s._fuel = v),
          ),
        ),
        _Section(
          title: '변속기',
          child: _ChipRow(
            items: _trans,
            value: s._transmission,
            onPick: (v) => s.rebuild(() => s._transmission = v),
          ),
        ),
        _Section(
          title: '지역',
          child: _ChipRow(
            items: _regions,
            value: s._region,
            onPick: (v) => s.rebuild(() => s._region = v),
          ),
        ),
      ],
    );
  }
}

class _OptionsStep extends StatelessWidget {
  const _OptionsStep(this.s);
  final _SellScreenState s;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Padding(
          padding: EdgeInsets.only(bottom: 14),
          child: Text(
            '차량이 보유한 옵션을 선택하세요. 매물 노출 점수에 반영됩니다.',
            style: TextStyle(color: AppColors.muted, fontSize: 13),
          ),
        ),
        for (final cat in categoryOrder) ...[
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Text(
              categoryLabel[cat]!,
              style: const TextStyle(
                color: AppColors.white,
                fontSize: 13,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: carOptions
                .where((o) => o.category == cat)
                .map((o) {
              final active = s._options.contains(o.key);
              return GestureDetector(
                onTap: () => s.rebuild(() {
                  if (active) {
                    s._options.remove(o.key);
                  } else {
                    s._options.add(o.key);
                  }
                }),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
                  decoration: BoxDecoration(
                    color: active ? AppColors.gold : const Color(0xFF0E1117),
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(
                      color: active
                          ? AppColors.gold
                          : Colors.white.withValues(alpha: 0.1),
                    ),
                  ),
                  child: Text(
                    o.label,
                    style: TextStyle(
                      color: active ? AppColors.black : AppColors.white,
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
        ],
        const SizedBox(height: 14),
        Text(
          '선택 ${s._options.length} / ${carOptions.length}',
          style: const TextStyle(color: AppColors.muted, fontSize: 11),
        ),
      ],
    );
  }
}

class _PriceAiStep extends StatelessWidget {
  const _PriceAiStep(this.s);
  final _SellScreenState s;

  @override
  Widget build(BuildContext context) {
    final est = s._priceEstimate;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Padding(
          padding: EdgeInsets.only(bottom: 14),
          child: Text(
            'AI가 입력하신 차량 정보를 바탕으로 예상 시세를 계산합니다.',
            style: TextStyle(color: AppColors.muted, fontSize: 13),
          ),
        ),
        GoldButton(
          label: 'AI 시세 계산하기',
          icon: Icons.auto_awesome,
          loading: s._priceLoading,
          expand: true,
          onPressed: s._runPricePrediction,
        ),
        if (est != null) ...[
          const SizedBox(height: 16),
          DarkCard(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  '예상 시세',
                  style: TextStyle(color: AppColors.muted, fontSize: 11),
                ),
                const SizedBox(height: 6),
                RichText(
                  text: TextSpan(
                    text:
                        '${formatKrw(est.priceRangeLow)} ~ ${formatKrw(est.priceRangeHigh)}',
                    style: const TextStyle(
                      color: AppColors.gold,
                      fontSize: 26,
                      fontWeight: FontWeight.w800,
                    ),
                    children: const [
                      TextSpan(
                        text: ' 만원',
                        style: TextStyle(
                          color: AppColors.muted,
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  '신뢰도 ${(est.confidence * 100).round()}%',
                  style: const TextStyle(color: AppColors.muted, fontSize: 11),
                ),
                const SizedBox(height: 14),
                GestureDetector(
                  onTap: () =>
                      s._price.text = est.predictedPrice.toString(),
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.05),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    alignment: Alignment.center,
                    child: Text(
                      '예측가(${formatKrw(est.predictedPrice)}만)로 설정',
                      style: const TextStyle(
                        color: AppColors.white,
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}

class _PricingStep extends StatelessWidget {
  const _PricingStep(this.s);
  final _SellScreenState s;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _Field(
          controller: s._price,
          label: '판매가 (만원)',
          hint: '3500',
          keyboardType: TextInputType.number,
        ),
        _Field(controller: s._title, label: '제목 (선택)', hint: '자동 생성됩니다'),
        _Field(
          controller: s._description,
          label: '상세 설명',
          maxLines: 4,
        ),
        GestureDetector(
          onTap: () => s.rebuild(() => s._negotiable = !s._negotiable),
          child: Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFF0E1117),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
            ),
            child: Row(
              children: [
                Container(
                  width: 20,
                  height: 20,
                  decoration: BoxDecoration(
                    color: s._negotiable ? AppColors.gold : Colors.transparent,
                    borderRadius: BorderRadius.circular(5),
                    border: s._negotiable
                        ? null
                        : Border.all(color: Colors.white.withValues(alpha: 0.2)),
                  ),
                  alignment: Alignment.center,
                  child: s._negotiable
                      ? const Icon(Icons.check, size: 12, color: AppColors.black)
                      : null,
                ),
                const SizedBox(width: 10),
                const Text(
                  '가격 협상 가능',
                  style: TextStyle(
                    color: AppColors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _ImagesStep extends StatelessWidget {
  const _ImagesStep(this.s);
  final _SellScreenState s;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Padding(
          padding: EdgeInsets.only(bottom: 14),
          child: Text(
            '차량 사진 최대 10장',
            style: TextStyle(color: AppColors.muted, fontSize: 13),
          ),
        ),
        GestureDetector(
          onTap: s._pickImages,
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 32),
            decoration: BoxDecoration(
              color: const Color(0xFF0E1117),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: Colors.white.withValues(alpha: 0.2),
                style: BorderStyle.solid,
              ),
            ),
            alignment: Alignment.center,
            child: Column(
              children: [
                const Icon(Icons.image_outlined, size: 30, color: AppColors.gold),
                const SizedBox(height: 8),
                Text(
                  '사진 선택 (${s._images.length}/10)',
                  style: const TextStyle(
                    color: AppColors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
          ),
        ),
        if (s._images.isNotEmpty) ...[
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: s._images
                .map((img) => ClipRRect(
                      borderRadius: BorderRadius.circular(10),
                      child: SizedBox(
                        width: 100,
                        height: 100,
                        child: Image.file(File(img.path), fit: BoxFit.cover),
                      ),
                    ))
                .toList(),
          ),
        ],
      ],
    );
  }
}

class _VideoStep extends StatelessWidget {
  const _VideoStep(this.s);
  final _SellScreenState s;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Padding(
          padding: EdgeInsets.only(bottom: 14),
          child: Text(
            '차량 한 바퀴 30~60초 영상을 업로드하면 3D 모델이 자동 생성됩니다.',
            style: TextStyle(color: AppColors.muted, fontSize: 13),
          ),
        ),
        Row(
          children: PipelineQuality.values.map((q) {
            final active = q == s._quality;
            final label = q == PipelineQuality.standard
                ? '표준'
                : q == PipelineQuality.hq
                    ? 'HQ'
                    : 'Ultra';
            return Expanded(
              child: Padding(
                padding: EdgeInsets.only(
                  right: q == PipelineQuality.ultra ? 0 : 8,
                ),
                child: GestureDetector(
                  onTap: () => s.rebuild(() => s._quality = q),
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    decoration: BoxDecoration(
                      color: active ? AppColors.gold : const Color(0xFF0E1117),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(
                        color: active
                            ? AppColors.gold
                            : Colors.white.withValues(alpha: 0.1),
                      ),
                    ),
                    alignment: Alignment.center,
                    child: Text(
                      label,
                      style: TextStyle(
                        color: active ? AppColors.black : AppColors.white,
                        fontSize: 13,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ),
              ),
            );
          }).toList(),
        ),
        const SizedBox(height: 14),
        GestureDetector(
          onTap: s._pickVideo,
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 32),
            decoration: BoxDecoration(
              color: const Color(0xFF0E1117),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.white.withValues(alpha: 0.2)),
            ),
            alignment: Alignment.center,
            child: Column(
              children: [
                const Icon(Icons.videocam_outlined,
                    size: 30, color: AppColors.gold),
                const SizedBox(height: 8),
                Text(
                  s._video != null ? '영상 선택됨 (변경)' : '영상 선택',
                  style: const TextStyle(
                    color: AppColors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 14),
        Row(
          children: [
            Expanded(
              child: OutlineGoldButton(
                label: '저장만',
                onPressed: s._submitLoading ? null : s._submit,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: GoldButton(
                label: s._video != null ? '등록 + 3D 생성' : '등록',
                icon: Icons.cloud_upload_outlined,
                loading: s._submitLoading,
                onPressed: s._submit,
              ),
            ),
          ],
        ),
        if (s._jobId != null) ...[
          const SizedBox(height: 18),
          PipelineStepperView(status: s._pipelineStatus),
        ],
      ],
    );
  }
}
